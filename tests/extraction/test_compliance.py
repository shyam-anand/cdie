from unittest.mock import Mock

import pytest

from cdie.extraction.findings import FINDING_KEYWORDS, FindingsExtractor
from cdie.models.audit import FindingType


class TestFindingsExtractor:
    """Test cases for FindingsExtractor"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_nlp = Mock()
        self.extractor = FindingsExtractor(self.mock_nlp)

    def test_extract_bullet_point_with_keyword(self):
        """Test extraction of bullet point with finding keyword"""
        text = "- Noncompliance found in safety procedures"

        results = list(self.extractor.extract(text))

        assert len(results) == 1
        assert results[0].issue == "Noncompliance found in safety procedures"
        assert results[0].confidence == 0.8
        assert results[0].type == FindingType.NON_COMPLIANCE

    def test_extract_asterisk_bullet(self):
        """Test extraction of asterisk bullet point"""
        text = "* Finding: Inadequate documentation"

        results = list(self.extractor.extract(text))

        assert len(results) == 1
        assert results[0].issue == "Finding: Inadequate documentation"
        assert results[0].confidence == 0.8

    def test_extract_dot_bullet(self):
        """Test extraction of dot bullet point"""
        text = "• Issue: Missing safety equipment"

        results = list(self.extractor.extract(text))

        assert len(results) == 1
        assert results[0].issue == "Issue: Missing safety equipment"
        assert results[0].confidence == 0.8

    def test_extract_numbered_bullet(self):
        """Test extraction of numbered bullet point"""
        text = "1. Violation: Improper waste disposal"

        results = list(self.extractor.extract(text))

        assert len(results) == 1
        assert results[0].issue == "1. Violation: Improper waste disposal"
        assert results[0].confidence == 0.8

    def test_extract_multiple_findings(self):
        """Test extraction of multiple findings"""
        text = """- Noncompliance found in safety procedures
        * Finding: Inadequate documentation
        • Issue: Missing safety equipment"""

        results = list(self.extractor.extract(text))

        assert len(results) == 3
        assert results[0].issue == "Noncompliance found in safety procedures"
        assert results[1].issue == "Finding: Inadequate documentation"
        assert results[2].issue == "Issue: Missing safety equipment"

    def test_extract_with_whitespace(self):
        """Test extraction with various whitespace patterns"""
        text = "   -   Noncompliance found in safety procedures   "

        results = list(self.extractor.extract(text))

        assert len(results) == 1
        assert results[0].issue == "Noncompliance found in safety procedures"

    def test_no_finding_keywords(self):
        """Test that lines without finding keywords are not extracted"""
        text = "- Regular procedure completed successfully"

        results = list(self.extractor.extract(text))

        assert len(results) == 0

    def test_case_insensitive_keyword_matching(self):
        """Test case insensitive keyword matching"""
        text = "- NONCOMPLIANCE found in safety procedures"

        results = list(self.extractor.extract(text))

        assert len(results) == 1
        assert results[0].issue == "NONCOMPLIANCE found in safety procedures"

    def test_mixed_case_keywords(self):
        """Test mixed case keywords"""
        text = "- Non-Compliance found in safety procedures"

        results = list(self.extractor.extract(text))

        assert len(results) == 1
        assert results[0].issue == "Non-Compliance found in safety procedures"

    def test_empty_text(self):
        """Test extraction with empty text"""
        text = ""

        results = list(self.extractor.extract(text))
        assert len(results) == 0

    def test_text_without_bullets(self):
        """Test extraction of text without bullet points"""
        text = "This is a regular paragraph without any bullet points"

        results = list(self.extractor.extract(text))
        assert len(results) == 0

    def test_finding_keywords_defined(self):
        """Test that finding keywords are properly defined"""
        assert len(FINDING_KEYWORDS) > 0
        assert all(isinstance(kw, str) for kw in FINDING_KEYWORDS)
        assert "noncompliance" in FINDING_KEYWORDS
        assert "finding" in FINDING_KEYWORDS
        assert "issue" in FINDING_KEYWORDS

    def test_confidence_scoring(self):
        """Test that all findings have consistent confidence scoring"""
        text = """- Noncompliance found in safety procedures
        * Finding: Inadequate documentation
        • Issue: Missing safety equipment"""

        results = list(self.extractor.extract(text))

        for result in results:
            assert result.confidence == 0.8

    def test_finding_type_consistency(self):
        """Test that all findings have consistent type"""
        text = """- Noncompliance found in safety procedures
        * Finding: Inadequate documentation
        • Issue: Missing safety equipment"""

        results = list(self.extractor.extract(text))

        for result in results:
            assert result.type == FindingType.NON_COMPLIANCE

    def test_bullet_stripping(self):
        """Test that bullet characters are properly stripped"""
        text = "- Noncompliance found in safety procedures"

        results = list(self.extractor.extract(text))

        assert len(results) == 1
        # Should strip the leading "- " but keep the rest
        assert results[0].issue == "Noncompliance found in safety procedures"

    def test_multiple_bullet_characters(self):
        """Test stripping of multiple bullet characters"""
        text = "--- Noncompliance found in safety procedures"

        results = list(self.extractor.extract(text))

        assert len(results) == 1
        assert results[0].issue == "Noncompliance found in safety procedures"

    def test_mixed_bullet_characters(self):
        """Test stripping of mixed bullet characters"""
        text = "-•* Noncompliance found in safety procedures"

        results = list(self.extractor.extract(text))

        assert len(results) == 1
        assert results[0].issue == "Noncompliance found in safety procedures"

    def test_keyword_in_middle_of_text(self):
        """Test finding keyword in middle of text"""
        text = "- Safety procedures show noncompliance with standards"

        results = list(self.extractor.extract(text))

        assert len(results) == 1
        assert results[0].issue == "Safety procedures show noncompliance with standards"

    def test_keyword_at_end_of_text(self):
        """Test finding keyword at end of text"""
        text = "- Safety procedures have a finding"

        results = list(self.extractor.extract(text))

        assert len(results) == 1
        assert results[0].issue == "Safety procedures have a finding"
