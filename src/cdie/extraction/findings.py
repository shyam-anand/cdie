"""
Extraction rules:
- Bullet detection: lines starting with -, •, *, r'\\d+\\.'.
- Keep only bullets containing one of the keywords in the ruleset.
- Narrative fallback:
    - Split paragraph into sentences.
    - Keep sentences with keyword match.
- Tables:
    - If header contains keyword, extract all cells in that column.
"""

import logging
from typing import Generator

from spacy.language import Language
from spacy.tokens import Doc

from cdie.extraction import rulesets
from cdie.extraction.confidence import Confidence, ConfidenceCriteria
from cdie.extraction.extractor import Extractor
from cdie.models import audit

logger = logging.getLogger(__name__)


FINDING_KEYWORDS = rulesets.load_ruleset("findings")


class FindingsExtractor(Extractor[audit.Finding]):
    def __init__(self, nlp: Language):
        confidence = Confidence()
        confidence.set_weight(ConfidenceCriteria.NEAR_KEYWORD, 0.5)
        # No regex or NER for findings
        confidence.set_weight(ConfidenceCriteria.REGEX_MATCH, 0.0)
        confidence.set_weight(ConfidenceCriteria.NER_MATCH, 0.0)

        super().__init__(nlp, confidence=confidence)
        self.max_distance = 700

    def extract(self, doc: Doc) -> Generator[audit.Finding, None, None]:
        matched_keywords: list[str] = []
        for keyword in FINDING_KEYWORDS:
            if keyword in doc.text:
                matched_keywords.append(keyword)

        if not matched_keywords:
            return

        for sentence in doc.sents:
            logger.info(f"Sentence: {sentence.text}")
            nearest_keyword, distance = self.nearest_keyword(
                doc.text, sentence.text, matched_keywords
            )
            logger.info(f"Nearest keyword: {nearest_keyword}, distance: {distance}")

            if distance < 0 or distance > self.max_distance:
                continue

            criteria = (
                (ConfidenceCriteria.NEAR_KEYWORD if bool(nearest_keyword) else 0)
                | ConfidenceCriteria.REGEX_MATCH
                | ConfidenceCriteria.NER_MATCH
            )
            confidence = self.confidence.calculate(criteria=criteria, distance=distance)

            if confidence > self.confidence_threshold:
                yield audit.Finding(
                    issue=sentence.text,
                    confidence=confidence,
                )
