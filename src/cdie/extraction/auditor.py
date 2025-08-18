import logging
from typing import Iterable

from spacy.language import Language
from spacy.tokens import Doc

from cdie.extraction import regexps
from cdie.extraction.confidence import ConfidenceCriteria
from cdie.extraction.extractor import Extractor
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


logger = logging.getLogger(__name__)


class AuditorExtractor(Extractor[audit.Auditor]):
    def __init__(self, nlp: Language):
        super().__init__(nlp)

    def extract(self, doc: Doc) -> Iterable[audit.Auditor]:
        for ent in doc.ents:
            logger.debug(f"Found {ent.label_}: '{ent.text}'")

            nearest_keyword = self.nearest_keyword(doc.text, ent.text, AUDITOR_KEYWORDS)
            logger.debug(f"Nearest keyword: '{nearest_keyword}'")

            ner_match = ent.label_ == "PERSON" or ent.label_ == "ORG"

            regex_match = (
                regexps.COMPANY_NAME.match(ent.text) or regexps.ORGANIZATION_NAME.match(ent.text)
                if ent.label_ == "ORG"
                else regexps.PERSON_NAME.match(ent.text)
            )

            criteria = (
                (ConfidenceCriteria.NEAR_KEYWORD if bool(nearest_keyword.keyword) else 0)
                | (ConfidenceCriteria.REGEX_MATCH if regex_match else 0)
                | (ConfidenceCriteria.NER_MATCH if ner_match else 0)
            )
            confidence = self.confidence.calculate(
                criteria=criteria, distance=nearest_keyword.distance
            )
            if confidence > self.confidence_threshold:
                yield audit.Auditor(
                    organization=audit.Organization(name=ent.text),
                    confidence=confidence,
                )
