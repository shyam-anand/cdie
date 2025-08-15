"""
confidence = base_score
           + 0.2 if near keyword
           + 0.1 if format/regex matches expected
           - 0.2 if OCR confidence < 80%
           + NER boost (0.1 - 0.15) if entity type matches expectation

base_score: 0.5 if found, 0.3 if inferred (role only, no name).
"""

import logging
from enum import IntFlag

logger = logging.getLogger(__name__)

# Boosts (or penalties)
NEAR_KEYWORD = 0.2
REGEX_MATCH = 0.2
NER_MATCH = 0.2

# Combination boosts (additional confidence when multiple factors agree)
REGEX_NER_COMBO = 0.05  # Extra boost when both regex and NER match
KEYWORD_REGEX_COMBO = 0.05  # Extra boost when both keyword and regex match
KEYWORD_NER_COMBO = 0.05  # Extra boost when both keyword and NER match
TRIPLE_COMBO = 0.05  # Extra boost when all three factors match


class ConfidenceCriteria(IntFlag):
    NEAR_KEYWORD = 1 << 0  # 1
    REGEX_MATCH = 1 << 1  # 2
    NER_MATCH = 1 << 2  # 4


SCORES: dict[int, float] = {
    ConfidenceCriteria.NEAR_KEYWORD: NEAR_KEYWORD,
    ConfidenceCriteria.REGEX_MATCH: REGEX_MATCH,
    ConfidenceCriteria.NER_MATCH: NER_MATCH,
    ConfidenceCriteria.REGEX_MATCH | ConfidenceCriteria.NER_MATCH: REGEX_NER_COMBO,
    ConfidenceCriteria.NEAR_KEYWORD | ConfidenceCriteria.REGEX_MATCH: KEYWORD_REGEX_COMBO,
    ConfidenceCriteria.NEAR_KEYWORD | ConfidenceCriteria.NER_MATCH: KEYWORD_NER_COMBO,
    ConfidenceCriteria.REGEX_MATCH
    | ConfidenceCriteria.NER_MATCH
    | ConfidenceCriteria.NEAR_KEYWORD: TRIPLE_COMBO,
}


class Confidence:
    def __init__(
        self,
        base: float = 0.0,
        *,
        scores: dict[int, float] = SCORES,
        penalize: bool = True,
    ):
        self.base = base
        self.scores = scores
        self.penalize = penalize

    def set_score(self, criteria: ConfidenceCriteria, score: float):
        self.scores[criteria] = score

    def calculate_distance_penalty(
        self,
        distance: int,
        no_penalty_threshold: int,
        penalty_threshold: int,
    ) -> float:
        """Calculate distance penalty that reduces the NEAR_KEYWORD boost.

        Args:
            distance: Distance value (0 = closest, higher = farther)

        Returns:
            Penalty value to subtract from the NEAR_KEYWORD boost.
            Positive values reduce the boost, negative values increase it.
        """
        if distance < no_penalty_threshold:
            return 0.0

        near_keyword_score = self.scores[ConfidenceCriteria.NEAR_KEYWORD]

        return (
            near_keyword_score
            * (distance - no_penalty_threshold)
            / (penalty_threshold - no_penalty_threshold)
        )

    def _get_criterion_boost(self, criteria: int, criterion: ConfidenceCriteria) -> float:
        """Get boost or penalty for a single criterion."""
        if criteria & criterion:
            boost = self.scores[criterion]
            logger.info(f"{criterion.name}, +{boost}")
            return boost
        elif self.penalize:
            penalty = -self.scores[criterion]
            logger.info(f"No {criterion.name}, {penalty}")
            return penalty
        return 0.0

    def _get_combo_boost(self, criteria: int, combo_key: int) -> float:
        """Get boost for a combination of criteria."""
        if criteria & combo_key == combo_key:
            boost = self.scores[combo_key]
            logger.info(f"Combo {combo_key}, +{boost}")
            return boost
        return 0.0

    def calculate(
        self,
        criteria: int,
        distance: int = -1,
        boost: float = 0.0,
        *,
        no_penalty_threshold: int = 50,
        penalty_threshold: int = 500,
    ) -> float:
        """Boost confidence based on various factors.

        Args:
            criteria: Bitwise combination of ConfidenceCriteria flags
                     (e.g., ConfidenceCriteria.NEAR_KEYWORD | ConfidenceCriteria.REGEX_MATCH)
            distance: Distance value for NEAR_KEYWORD criterion. Used to calculate non-linear
            penalty.
                     -1 means no distance penalty applied.

        Returns:
            Boosted confidence score between 0.0 and 1.0

        Note:
            - Individual criteria boost confidence when present
            - Missing criteria penalize confidence when penalize=True
            - Combinations of criteria provide additional confidence boosts
            - NEAR_KEYWORD boost is applied normally, then distance penalty is subtracted
            - Distance penalty: additional boost for distances 0-10, no penalty for 10-20,
              gradual penalty for 20-50, steeper penalty for 50-100, max penalty for 100+
            - Final confidence is capped at 1.0
        """
        logger.info(f"Base score: {self.base=}")

        # Calculate individual criteria boosts
        individual_criteria_score = sum(
            self._get_criterion_boost(criteria, criterion) for criterion in ConfidenceCriteria
        )

        # Calculate combination boosts
        combos = [
            ConfidenceCriteria.REGEX_MATCH | ConfidenceCriteria.NER_MATCH,
            ConfidenceCriteria.NEAR_KEYWORD | ConfidenceCriteria.REGEX_MATCH,
            ConfidenceCriteria.NEAR_KEYWORD | ConfidenceCriteria.NER_MATCH,
            (
                ConfidenceCriteria.REGEX_MATCH
                | ConfidenceCriteria.NER_MATCH
                | ConfidenceCriteria.NEAR_KEYWORD
            ),
        ]

        combo_criteria_score = sum(
            self._get_combo_boost(criteria, combo_key) for combo_key in combos
        )

        # Apply distance penalty for NEAR_KEYWORD criterion
        distance_penalty = self.calculate_distance_penalty(
            distance, no_penalty_threshold, penalty_threshold
        )
        logger.info(f"Penalty for distance {distance}: {distance_penalty:.3f}")

        # Sum all boosts (including NEAR_KEYWORD boost)
        score = individual_criteria_score + combo_criteria_score - distance_penalty
        logger.info(
            f"{individual_criteria_score=} + {combo_criteria_score=} - "
            f"{distance_penalty=} = {score=:.2f}"
        )

        confidence = min(1.0, self.base + score + boost)
        logger.info(f"Confidence: {self.base=} + {score=} + {boost=} = {confidence:.2f}")
        return confidence


# Usage example:
if __name__ == "__main__":
    # Create confidence calculator
    conf = Confidence(base=0.5)

    # Example: Entity has both regex match and NER match
    criteria = ConfidenceCriteria.REGEX_MATCH | ConfidenceCriteria.NER_MATCH
    confidence = conf.calculate(criteria)
    print(f"Regex + NER match: {confidence:.2f}")

    # Example: Entity has all three criteria
    criteria = (
        ConfidenceCriteria.NEAR_KEYWORD
        | ConfidenceCriteria.REGEX_MATCH
        | ConfidenceCriteria.NER_MATCH
    )
    confidence = conf.calculate(criteria)
    print(f"All criteria match: {confidence:.2f}")

    # Example: Entity has only keyword proximity
    criteria = ConfidenceCriteria.NEAR_KEYWORD
    confidence = conf.calculate(criteria)
    print(f"Only keyword match: {confidence:.2f}")
