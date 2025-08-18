from cdie.extraction.confidence import Confidence, ConfidenceCriteria


class TestConfidence:
    def test_individual_criteria_boosts(self):
        """Test that individual criteria provide correct boosts."""
        conf = Confidence(base=0.5)

        # Test each individual criterion
        confidence = conf.calculate(ConfidenceCriteria.NEAR_KEYWORD)
        assert confidence == 0.7  # 0.5 + 0.2

        confidence = conf.calculate(ConfidenceCriteria.REGEX_MATCH)
        assert confidence == 0.7  # 0.5 + 0.2

        confidence = conf.calculate(ConfidenceCriteria.NER_MATCH)
        assert confidence == 0.7  # 0.5 + 0.2

    def test_combination_boosts(self):
        """Test that combinations provide additional boosts."""
        conf = Confidence(base=0.5)

        # Test regex + NER combination
        criteria = ConfidenceCriteria.REGEX_MATCH | ConfidenceCriteria.NER_MATCH
        confidence = conf.calculate(criteria)
        # 0.5 + 0.2 + 0.2 + 0.1 (combo) = 1.0 (capped)
        assert confidence == 1.0

        # Test keyword + regex combination
        criteria = ConfidenceCriteria.NEAR_KEYWORD | ConfidenceCriteria.REGEX_MATCH
        confidence = conf.calculate(criteria)
        # 0.5 + 0.2 + 0.2 + 0.1 (combo) = 1.0 (capped)
        assert confidence == 1.0

    def test_triple_combo_boost(self):
        """Test that all three criteria provide maximum boost."""
        conf = Confidence(base=0.5)

        criteria = (
            ConfidenceCriteria.NEAR_KEYWORD
            | ConfidenceCriteria.REGEX_MATCH
            | ConfidenceCriteria.NER_MATCH
        )
        confidence = conf.calculate(criteria)
        # 0.5 + 0.2 + 0.2 + 0.2 + 0.1 + 0.1 + 0.1 + 0.2 (triple) = 1.6 (capped at 1.0)
        assert confidence == 1.0

    def test_penalties_when_criteria_missing(self):
        """Test that missing criteria are penalized when penalize=True."""
        conf = Confidence(base=0.5, penalize=True)

        # No criteria should result in penalties
        confidence = conf.calculate(0)
        # 0.5 - 0.2 - 0.2 - 0.2 = -0.1 (but should be capped at 0.0)
        assert confidence == 0.0

    def test_no_penalties_when_penalize_false(self):
        """Test that missing criteria are not penalized when penalize=False."""
        conf = Confidence(base=0.5, penalize=False)

        # No criteria should not result in penalties
        confidence = conf.calculate(0)
        assert confidence == 0.5

    def test_confidence_capping(self):
        """Test that confidence is properly capped at 1.0."""
        conf = Confidence(base=0.8)  # Higher base to test capping

        criteria = (
            ConfidenceCriteria.NEAR_KEYWORD
            | ConfidenceCriteria.REGEX_MATCH
            | ConfidenceCriteria.NER_MATCH
        )
        confidence = conf.calculate(criteria)
        # Should be capped at 1.0 even if calculation exceeds it
        assert confidence == 1.0

    def test_keywords_near_function(self):
        """Test the keywords_near function."""
        conf = Confidence()
        text = "The audit was conducted by John Smith on January 15, 2024"
        keywords = ["audit", "conducted", "John"]

        matches = conf.keywords_near(text, keywords)
        assert len(matches) == 3
        assert ("audit", 4) in matches
        assert ("conducted", 18) in matches
        assert ("John", 35) in matches

    def test_keywords_near_with_distance_limit(self):
        """Test keywords_near with distance limit."""
        conf = Confidence()
        text = "The audit was conducted by John Smith on January 15, 2024"
        keywords = ["audit", "conducted", "John"]

        # Only keywords within first 20 characters
        matches = conf.keywords_near(text, keywords, max_distance=20)
        assert len(matches) == 2
        assert ("audit", 4) in matches
        assert ("conducted", 18) in matches
        assert ("John", 35) not in matches  # Beyond max_distance
