import logging
import re
from typing import Generator

from spacy.language import Language
from spacy.tokens import Doc

from cdie.extraction.confidence import Confidence, ConfidenceCriteria
from cdie.extraction.extractors.extractor import Extractor
from cdie.models import audit

COMPANY_NAME_REGEXP = re.compile(
    r"((\b(?:[A-Z][a-zA-Z&]+(?:\s+[A-Z][a-zA-Z&]+|\ &|\sand)*)\s+)+"
    r"(?:(?:Ltd|Limited|Inc|Corporation|Co|Company)[\.,]*\s*)+\b)",
    re.MULTILINE,
)
SUPPLIER_KEYWORDS_REGEXP = [
    re.compile(regexp, re.IGNORECASE)
    for regexp in [
        r"\b(facilit(?:y|ies)(?:\s+names?)?)\b",
        r"\b(factor(?:y|ies)(?:\s+names?)?)\b",
        r"\b(supplier(?:s)?(?:\s+names?)?)\b",
        r"\b(plant(?:s)?(?:\s+names?)?)\b",
        r"\b(mill(?:s)?(?:\s+names?)?)\b",
        r"\b(manufacturer(?:s)?(?:\s+names?)?)\b",
        r"\b(contract factory(?:s)?(?:\s+names?)?)\b",
        r"\b(production site(?:s)?(?:\s+names?)?)\b",
        r"\b(monitoring firm(?:s)?(?:\s+names?)?)\b",
    ]
]

logger = logging.getLogger(__name__)


class SupplierExtractor(Extractor[audit.Supplier]):
    def __init__(self, nlp: Language):
        confidence = Confidence()
        confidence.set_score(ConfidenceCriteria.REGEX_MATCH, 0.3)
        confidence.set_score(ConfidenceCriteria.NEAR_KEYWORD, 0.3)
        confidence.set_score(ConfidenceCriteria.NER_MATCH, 0.1)
        super().__init__(nlp, confidence=confidence)

    def nearest_keyword_with_indices(
        self,
        text: str,
        word: str,
        keyword_list: set[tuple[str, int, int]],
        max_distance: int = 100,
    ) -> tuple[str | None, int]:
        lower_text = text.lower()
        word_start = lower_text.find(word.lower())
        word_end = word_start + len(word)
        nearest_keyword: tuple[str, int | float] = ("", float("inf"))
        for kw, kw_start, kw_end in keyword_list:
            distance = self._distance(word_start, word_end, kw_start, kw_end)
            logger.info(f"Keyword '{kw}' found at {distance}")
            if distance > 0 and distance < nearest_keyword[1]:
                nearest_keyword = (kw, distance)
        return nearest_keyword[0], int(nearest_keyword[1])

    def _get_keywords(self, text: str) -> set[tuple[str, int, int]]:
        keywords: set[tuple[str, int, int]] = set()
        for keyword_regexp in SUPPLIER_KEYWORDS_REGEXP:
            for match in keyword_regexp.finditer(text):
                keywords.add((match.group(0), match.start(), match.end()))
        return keywords

    def extract(self, doc: Doc) -> Generator[audit.Supplier, None, None]:
        keywords = self._get_keywords(doc.text)
        logger.info(f"keywords: {keywords}")

        if not keywords:
            logger.info("No supplier keywords found")
            return

        for regex_match in COMPANY_NAME_REGEXP.finditer(doc.text):
            organization = audit.Organization(name=regex_match.group(0))

            entities = self.nlp(organization.name).ents
            entity_label = next(
                (ent.label_ for ent in entities if ent.label_ == "ORG" or ent.label_ == "PERSON"),
                None,
            )

            logger.info(f"Found {entity_label}: '{organization.name}'")
            nearest_keyword, distance = self.nearest_keyword_with_indices(
                doc.text, organization.name, keywords
            )
            if distance < 0:
                continue
            criteria = (
                ConfidenceCriteria.REGEX_MATCH
                | (ConfidenceCriteria.NEAR_KEYWORD if bool(nearest_keyword) else 0)
                | (ConfidenceCriteria.NER_MATCH if entity_label else 0)
            )
            confidence = self.confidence.calculate(
                criteria=criteria,
                distance=distance,
                no_penalty_threshold=100,
                penalty_threshold=700,
            )
            if confidence > self.confidence_threshold:
                yield audit.Supplier(
                    organization=organization,
                    type=nearest_keyword,
                    confidence=confidence,
                )
