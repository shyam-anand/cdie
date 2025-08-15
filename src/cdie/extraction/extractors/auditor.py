import logging
import re
from typing import Generator

from spacy.language import Language
from spacy.tokens import Doc

from cdie.extraction.confidence import Confidence, ConfidenceCriteria
from cdie.extraction.extractors.extractor import Extractor
from cdie.models import audit

AUDITOR_KEYWORDS = [
    "auditor",
    "audited by",
    "inspected by",
    "inspection conducted by",
    "compliance manager",
    "monitor",
    "assessor",
    "evaluation by",
]

# Captures names (e.g. John Doe, Jesus H. Christ)
name_regexp = r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]*\.?)+\b"
company_name_regexp = (
    r"\b(?:[A-Z][a-zA-Z&]+(?:\s+[A-Z][a-zA-Z&]+)*)\s+"
    r"(?:Ltd|Limited|Inc|Corporation|Co|Company)\.?\b"
)
org_name_regexp = r"\b(?:the\s+)?(?:[A-Z][a-zA-Z&]+(?:\s+[A-Z][a-zA-Z&]+)*)\n"

logger = logging.getLogger(__name__)

BASE_SCORE = 0.0


class AuditorExtractor(Extractor[audit.Auditor]):
    def __init__(self, nlp: Language):
        confidence = Confidence(base=BASE_SCORE)
        super().__init__(nlp, confidence=confidence)

    def extract(self, doc: Doc) -> Generator[audit.Auditor, None, None]:
        for ent in doc.ents:
            if ent.label_ == "PERSON" and re.match(name_regexp, ent.text):
                logger.info(f"Found {ent.label_}: '{ent.text}'")

                nearest_keyword, distance = self.nearest_keyword(
                    doc.text, ent.text, AUDITOR_KEYWORDS
                )

                criteria = (
                    (ConfidenceCriteria.NEAR_KEYWORD if bool(nearest_keyword) else 0)
                    | ConfidenceCriteria.REGEX_MATCH
                    | ConfidenceCriteria.NER_MATCH
                )
                confidence = self.confidence.calculate(criteria=criteria, distance=distance)
                if confidence > self.confidence_threshold:
                    yield audit.Auditor(name=ent.text, confidence=confidence)
            elif ent.label_ == "ORG":
                nearest_keyword, distance = self.nearest_keyword(
                    doc.text, ent.text, AUDITOR_KEYWORDS
                )
                if (
                    (re.match(company_name_regexp, ent.text) or re.match(org_name_regexp, ent.text))
                    and nearest_keyword
                    and distance >= 0  # Avoid keywords within the name (false positives)
                ):
                    logger.info(f"Found {ent.label_}: '{ent.text}'")
                    logger.info(f"Nearest keyword: '{nearest_keyword}' at distance {distance}")
                    criteria = (
                        (ConfidenceCriteria.NEAR_KEYWORD if bool(nearest_keyword) else 0)
                        | ConfidenceCriteria.REGEX_MATCH
                        | ConfidenceCriteria.NER_MATCH
                    )
                    confidence = self.confidence.calculate(criteria=criteria, distance=distance)
                    yield audit.Auditor(
                        organization=audit.Organization(name=ent.text),
                        confidence=confidence,
                    )
