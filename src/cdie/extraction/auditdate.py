import logging
import re
from datetime import date, datetime
from enum import Enum
from typing import Generator

from spacy.language import Language

from cdie.extraction.confidence import Confidence, ConfidenceCriteria
from cdie.extraction.extractor import Extractor
from cdie.extraction.textutils import keywords
from cdie.ingestion.pdfparser import PageData
from cdie.models import audit

logger = logging.getLogger(__name__)

# Exact YYYY-MM-DD -> 0.9-1.0
SCORE_EXACT = 0.5
# Month & year only -> 0.7-0.8
SCORE_MONTH_YEAR = 0.4

MONTH_NAMES = [
    "Jan(?:uary)?",
    "Feb(?:ruary)?",
    "Mar(?:ch)?",
    "Apr(?:il)?",
    "May",
    "Jun(?:e)?",
    "Jul(?:y)?",
    "Aug(?:ust)?",
    "Sep(?:tember)?",
    "Oct(?:ober)?",
    "Nov(?:ember)?",
    "Dec(?:ember)?",
]

MONTH_NAMES_REGEX = r"\b(?:" + "|".join(MONTH_NAMES) + r")\b"

DATE_KEYWORDS = keywords.load_keywords("auditdate")


class DateFormat(Enum):
    # TODO: Handle US format (MM/DD/YYYY)
    ISO = (
        r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b",
        SCORE_EXACT,
        True,
    )

    # D Month YYYY: 14 August 2025
    DAY_MONTH_YEAR = (
        r"\b\d{1,2}\s+" + MONTH_NAMES_REGEX + r"\s+\d{4}\b",
        SCORE_EXACT,
        False,
        [
            "%d %B %Y",  # 14 August 2025
            "%d %b %Y",  # 14 Aug 2025
        ],
    )

    # Month D, YYYY: August 14, 2025
    MONTH_DAY_YEAR = (
        MONTH_NAMES_REGEX + r"\s+\d{1,2},\s+\d{4}\b",
        SCORE_EXACT,
        False,
        [
            "%B %d, %Y",  # August 14, 2025
            "%B %d, %Y",  # Aug 14, 2025
        ],
    )

    # Month YYYY: August 2025
    MONTH_YEAR = (
        MONTH_NAMES_REGEX + r"\s+\d{4}\b",
        SCORE_MONTH_YEAR,
        False,
        [
            "%B %Y",  # August 2025
            "%b %Y",  # Aug 2025
        ],
    )

    def __init__(
        self,
        regexp: str,
        score: float,
        is_iso: bool = False,
        formats: list[str] = [],
    ):
        self.regexp = re.compile(regexp, re.IGNORECASE)
        self.score = score
        self.is_iso = is_iso
        self.formats = formats

    def normalize(self, date_string: str) -> date:
        if self.is_iso:
            return datetime.fromisoformat(date_string).date()

        for format in self.formats:
            try:
                return datetime.strptime(date_string, format).date()
            except ValueError:
                continue
        raise ValueError(f"Invalid date string: {date_string}")


class AuditDateExtractor(Extractor[audit.AuditDate]):
    def __init__(self, nlp: Language):
        confidence = Confidence()
        # Ignore NER and REGEX matches, because they are always True
        confidence.set_weight(ConfidenceCriteria.NER_MATCH, 0.0)
        confidence.set_weight(ConfidenceCriteria.REGEX_MATCH, 0.0)
        # NEAR_KEYWORD is the only meaningful score, so set a high weight for it
        confidence.set_weight(ConfidenceCriteria.NEAR_KEYWORD, 0.3)
        super().__init__(nlp, confidence=confidence)

    def extract(self, page_data: PageData) -> Generator[audit.AuditDate, None, None]:
        """Extracts audit dates from text.
        This method first looks for date patterns, and then checks if it's near a date
        keyword.
        """
        for date_format in DateFormat:
            for match in date_format.regexp.findall(page_data.text):
                nearest_keyword, distance = self.nearest_keyword(
                    page_data.text, match, DATE_KEYWORDS
                )

                # The nearer the keyword, the higher the boost
                # If over 200 characters, penalize
                distance_boost = (1.0 - (distance / 200)) if distance > -1 else 0.0

                confidence = self.confidence.calculate(
                    criteria=ConfidenceCriteria.NEAR_KEYWORD if distance > -1 else 0,
                    distance=distance,
                    boost=distance_boost,
                )
                logger.info(
                    f"Date format {date_format.name} found: {match}, confidence: {confidence}"
                )

                date = date_format.normalize(match)
                yield audit.AuditDate(
                    date=date,
                    confidence=confidence,
                    context={
                        "page_number": page_data.page_number,
                        "keyword": nearest_keyword,
                    },
                )
