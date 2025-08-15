import abc
import logging
from typing import Generator, Generic, TypeVar

from spacy.language import Language
from spacy.tokens import Doc

from cdie.extraction.confidence import Confidence
from cdie.models.audit import Extracted

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Extracted)

CONFIDENCE_THRESHOLD = 0.5


class Extractor(abc.ABC, Generic[T]):
    def __init__(
        self,
        nlp: Language,
        confidence_threshold: float = CONFIDENCE_THRESHOLD,
        confidence: Confidence = Confidence(),
    ):
        self.nlp = nlp
        self.confidence_threshold = confidence_threshold
        self.confidence = confidence

    def _distance(
        self,
        word_one_start: int,
        word_one_end: int,
        word_two_start: int,
        word_two_end: int,
    ) -> int:
        return max(word_one_start, word_two_start) - min(word_one_end, word_two_end)

    def _keywords_near(
        self,
        full_text: str,
        word: str,
        keyword_list: list[str],
        max_distance: int = 400,
    ) -> list[tuple[str, int]]:
        lower_text = full_text.lower()
        matched_keywords: list[tuple[str, int]] = []
        for kw in keyword_list:
            if kw in lower_text:
                word_at = lower_text.find(word.lower())
                kw_at = lower_text.find(kw.lower())
                distance = self._distance(word_at, word_at + len(word), kw_at, kw_at + len(kw))
                logger.info(f"Keyword '{kw}' found at {distance}")
                if distance <= max_distance:
                    matched_keywords.append((kw, distance))
        return matched_keywords

    def nearest_keyword(
        self,
        full_text: str,
        word: str,
        keyword_list: list[str],
        max_distance: int = 400,
    ) -> tuple[str | None, int]:
        """
        Find the nearest keyword to the word in the full text.
        """
        matched_keywords = self._keywords_near(full_text, word, keyword_list, max_distance)
        if matched_keywords:
            nearest_keyword = min(matched_keywords, key=lambda x: x[1])
            logger.info(f"Nearest keyword: {nearest_keyword}")
            return nearest_keyword
        return None, -1

    @abc.abstractmethod
    def extract(self, doc: Doc) -> Generator[T, None, None]:
        pass
