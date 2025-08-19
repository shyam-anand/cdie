import logging
import re
from typing import Iterable

from spacy.language import Language

from cdie.extraction.confidence import Confidence, ConfidenceCriteria
from cdie.extraction.extractor import Extractor, NearestKeyword, no_nearest_keyword
from cdie.extraction.textutils import regexps
from cdie.ingestion.pdfparser import PageData
from cdie.models import audit

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
        confidence.set_weight(ConfidenceCriteria.REGEX_MATCH, 0.0)
        confidence.set_weight(ConfidenceCriteria.NEAR_KEYWORD, 0.3)
        confidence.set_weight(ConfidenceCriteria.NER_MATCH, 0.1)
        super().__init__(nlp, confidence=confidence)

    def nearest_keyword_with_indices(
        self,
        text: str,
        word: str,
        keyword_list: set[tuple[str, int, int]],
    ) -> NearestKeyword:
        """
        Finds the keyword closest to the specified word in the text.

        Args:
            text: The text to search in
            word: The word to find the nearest keyword for
            keyword_list: Set of (keyword, start_index, end_index) tuples representing
                         pre-extracted keywords with their positions in the text

        Returns:
            A tuple of (keyword, distance) where distance is the character distance
            between the word and keyword. Returns ("", 1000) if no valid keyword
            is found within the search criteria.
        """
        lower_text = text.lower()
        word_start = lower_text.find(word.lower())
        word_end = word_start + len(word)
        nearest_keyword: NearestKeyword = no_nearest_keyword
        for kw, kw_start, kw_end in keyword_list:
            distance = self._distance(word_start, word_end, kw_start, kw_end)
            logger.debug(f"Keyword '{kw}' found at {distance}")
            if (
                distance >= 0 and distance < nearest_keyword.distance
            ) or nearest_keyword.distance == -1:
                nearest_keyword = NearestKeyword(kw, distance)
        return nearest_keyword

    def _get_keywords(self, text: str) -> set[tuple[str, int, int]]:
        keywords: set[tuple[str, int, int]] = set()
        for keyword_regexp in SUPPLIER_KEYWORDS_REGEXP:
            for match in keyword_regexp.finditer(text):
                keywords.add((match.group(0), match.start(), match.end()))
        return keywords

    def extract_from_tables(
        self,
        page_data: PageData,
        keywords: set[tuple[str, int, int]],
    ) -> Iterable[audit.Supplier]:
        """Extract suppliers and factories from table data"""

        for table in page_data.tables:
            if not table or len(table) < 2:
                continue

            # Look for supplier/factory columns
            header_row = table[0] if table[0] else []
            supplier_cols: list[tuple[int, NearestKeyword]] = []

            for i, header in enumerate(header_row):
                if header:
                    nearest_keyword = self.nearest_keyword_with_indices(
                        page_data.text, header, keywords
                    )
                    if nearest_keyword.distance >= 0:
                        supplier_cols.append((i, nearest_keyword))

            # Extract data from identified columns
            for row in table[1:]:  # Skip header row
                if not row:
                    continue

                for col_idx, nearest_keyword in supplier_cols:
                    if col_idx < len(row) and row[col_idx]:
                        name = str(row[col_idx]).strip()

                        criteria = ConfidenceCriteria.NEAR_KEYWORD
                        if regexps.is_company_name(name):
                            doc = self.nlp(name)
                            if any(ent.label_ == "ORG" for ent in doc.ents):
                                criteria |= ConfidenceCriteria.NER_MATCH
                            confidence = self.confidence.calculate(
                                criteria=criteria,
                                distance=nearest_keyword.distance,
                            )
                            yield audit.Supplier(
                                organization=audit.Organization(name=name),
                                type=nearest_keyword.keyword,
                                confidence=confidence,
                                context={"page_number": page_data.page_number},
                            )

    def _extract_from_text(
        self, page_data: PageData, keywords: set[tuple[str, int, int]]
    ) -> Iterable[audit.Supplier]:
        for regex_match in regexps.COMPANY_NAME.finditer(page_data.text):
            name = regex_match.group(0)

            nearest_keyword = self.nearest_keyword_with_indices(page_data.text, name, keywords)
            if nearest_keyword.distance < 0:
                continue

            criteria = ConfidenceCriteria.REGEX_MATCH | ConfidenceCriteria.NEAR_KEYWORD

            doc = self.nlp(name)
            if any(ent.label_ == "ORG" for ent in doc.ents):
                criteria |= ConfidenceCriteria.NER_MATCH

            confidence = self.confidence.calculate(
                criteria=criteria,
                distance=nearest_keyword.distance,
                no_penalty_threshold=100,
                penalty_threshold=700,
            )
            if confidence > self.confidence_threshold:
                yield audit.Supplier(
                    organization=audit.Organization(name=name),
                    type=nearest_keyword.keyword,
                    confidence=confidence,
                    context={"page_number": page_data.page_number},
                )

    def extract(self, page_data: PageData) -> Iterable[audit.Supplier]:
        keywords = self._get_keywords(page_data.text)
        logger.debug(f"keywords: {keywords}")

        if not keywords:
            logger.debug("No supplier keywords found")
            return

        yield from self._extract_from_text(page_data, keywords)
        if page_data.tables:
            yield from self.extract_from_tables(page_data, keywords)
