import logging
import re
from typing import Iterable

from spacy.language import Language

from cdie.extraction.confidence import ConfidenceCriteria
from cdie.extraction.extractor import Extractor
from cdie.extraction.textutils import regexps
from cdie.ingestion.pdfparser import PageData
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

AUDITOR_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        # Auditor name patterns
        r"(?:auditor|inspector|assessor|examiner|reviewer)[\s:]*([A-Z][a-z]+\s+[A-Z][a-z]+)",
        r"(?:conducted\s+by|performed\s+by|led\s+by)[\s:]*([A-Z][a-z]+\s+[A-Z][a-z]+)",
        r"(?:audit\s+team|inspection\s+team)[\s:]*([A-Z][a-z]+\s+[A-Z][a-z]+)",
        r"(?:principal\s+auditor|lead\s+auditor)[\s:]*([A-Z][a-z]+\s+[A-Z][a-z]+)",
        # Auditor company patterns
        r"(?:audit\s+firm|auditing\s+company|consulting\s+firm)[\s:]*([A-Z][A-Za-z\s&,]+(?:LLC|Inc|Ltd|Corporation|Corp|LLP|LTD)?)",
        r"(?:conducted\s+by|performed\s+by)\s+([A-Z][A-Za-z\s&,]+(?:LLC|Inc|Ltd|Corporation|Corp|LLP|LTD))",
        r"([A-Z][A-Za-z\s&,]+(?:LLC|Inc|Ltd|Corporation|Corp|LLP|LTD))\s+(?:audit|assessment|inspection)",
    ]
]

logger = logging.getLogger(__name__)


class AuditorExtractor(Extractor[audit.Auditor]):
    def __init__(self, nlp: Language):
        super().__init__(nlp)

    def _extract(self, text: str, substring: str, page_number: int) -> Iterable[audit.Auditor]:
        nearest_keyword = self.nearest_keyword(text, substring, AUDITOR_KEYWORDS)
        if not nearest_keyword.keyword:
            return
        logger.debug(f"Nearest keyword: '{nearest_keyword}'")
        criteria = ConfidenceCriteria.NEAR_KEYWORD

        doc = self.nlp(substring)
        if any(ent.label_ == "PERSON" or ent.label_ == "ORG" for ent in doc.ents):
            criteria |= ConfidenceCriteria.NER_MATCH

        if regexps.is_person_name(substring):
            confidence = self.confidence.calculate(
                criteria | ConfidenceCriteria.REGEX_MATCH, nearest_keyword.distance
            )
            yield audit.Auditor(
                name=substring, confidence=confidence, context={"page_number": page_number}
            )
        elif regexps.is_company_name(substring) or regexps.is_organization_name(substring):
            confidence = self.confidence.calculate(
                criteria | ConfidenceCriteria.REGEX_MATCH, nearest_keyword.distance
            )
            yield audit.Auditor(
                organization=audit.Organization(name=substring),
                confidence=confidence,
                context={"page_number": page_number},
            )

    def extract_auditor_from_tables(self, page_data: PageData) -> Iterable[audit.Auditor]:
        """Extracts auditor info from table data"""

        # Look for rows that might contain auditor information
        for row in page_data.tables:
            if not row or len(row) < 2:
                continue

            row_text = " ".join(str(cell) for cell in row if cell).lower()

            # Found a potential auditor row
            for cell in row:
                if cell and isinstance(cell, str):
                    cell = cell.strip()
                    if len(cell) <= 3:  # Skip very short entries
                        continue

                    for auditor in self._extract(row_text, cell, page_data.page_number):
                        yield auditor

    def extract_auditor_info(self, page_data: PageData) -> Iterable[audit.Auditor]:
        """Extracts auditor name and company from text and table data"""

        # Try to extract from main text
        for pattern in AUDITOR_PATTERNS:
            matches = pattern.findall(page_data.text)
            if matches:
                match = matches[0].strip()

                for auditor in self._extract(page_data.text, match, page_data.page_number):
                    yield auditor

    def extract(self, page_data: PageData) -> Iterable[audit.Auditor]:
        yield from self.extract_auditor_info(page_data)
        if page_data.tables:
            yield from self.extract_auditor_from_tables(page_data)
