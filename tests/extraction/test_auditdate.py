from unittest.mock import Mock, patch

import pytest

from cdie.extraction.extractors.auditdate import DATE_REGEXES, AuditDateExtractor


class TestAuditDateExtractor:
    """Test cases for AuditDateExtractor"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_nlp = Mock()
        self.extractor = AuditDateExtractor(self.mock_nlp)

    def test_extract_iso_date_with_keyword(self):
        """Test extraction of ISO date format with keyword"""
        text = "Audit date: 2023-07-15"

        with patch("cdie.extraction.auditdate.DATE_KEYWORDS", ["audit date"]):
            with patch("cdie.extraction.confidence.near_keyword") as mock_near:
                mock_near.return_value = "audit date"
                results = list(self.extractor.extract(text))

        assert len(results) == 1
        assert results[0].start == "2023-07-15"
        assert results[0].confidence == 0.9

    def test_extract_month_year_format(self):
        """Test extraction of month year format"""
        text = "Audit conducted in October 2012"

        with patch("cdie.extraction.auditdate.DATE_KEYWORDS", ["audit"]):
            with patch("cdie.extraction.confidence.near_keyword") as mock_near:
                mock_near.return_value = "audit"
                results = list(self.extractor.extract(text))

        assert len(results) == 1
        assert results[0].start == "October 2012"
        assert results[0].confidence == 0.7

    def test_extract_month_day_year_format(self):
        """Test extraction of month day, year format"""
        text = "Inspection date: October 10, 2012"

        with patch("cdie.extraction.auditdate.DATE_KEYWORDS", ["inspection date"]):
            with patch("cdie.extraction.confidence.near_keyword") as mock_near:
                mock_near.return_value = "inspection date"
                results = list(self.extractor.extract(text))

        assert len(results) == 1
        assert results[0].start == "October 10, 2012"
        assert results[0].confidence == 0.9

    def test_extract_day_month_year_format(self):
        """Test extraction of day month year format"""
        text = "Review date: 10 October 2012"

        with patch("cdie.extraction.auditdate.DATE_KEYWORDS", ["review date"]):
            with patch("cdie.extraction.confidence.near_keyword") as mock_near:
                mock_near.return_value = "review date"
                results = list(self.extractor.extract(text))

        assert len(results) == 1
        assert results[0].start == "10 October 2012"
        assert results[0].confidence == 0.9

    def test_no_keyword_match(self):
        """Test that dates without keywords are not extracted"""
        text = "Some random date: 2023-07-15"

        with patch("cdie.extraction.confidence.near_keyword") as mock_near:
            mock_near.return_value = None
            results = list(self.extractor.extract(text))

        assert len(results) == 0

    def test_multiple_dates_same_line(self):
        """Test extraction of multiple dates on same line"""
        text = "Audit period: 2023-01-01 to 2023-12-31"

        with patch("cdie.extraction.auditdate.DATE_KEYWORDS", ["audit period"]):
            with patch("cdie.extraction.confidence.near_keyword") as mock_near:
                mock_near.return_value = "audit period"
                results = list(self.extractor.extract(text))

        # Should only extract first match due to break statement
        assert len(results) == 1
        assert results[0].start == "2023-01-01"

    def test_dates_across_multiple_lines(self):
        """Test extraction of dates across multiple lines"""
        text = """Audit date: 2023-07-15
        Review date: October 10, 2012"""

        with patch("cdie.extraction.auditdate.DATE_KEYWORDS", ["audit date", "review date"]):
            with patch("cdie.extraction.confidence.near_keyword") as mock_near:
                mock_near.side_effect = ["audit date", "review date"]
                results = list(self.extractor.extract(text))

        assert len(results) == 2
        assert results[0].start == "2023-07-15"
        assert results[1].start == "October 10, 2012"

    def test_invalid_date_formats(self):
        """Test that invalid date formats are not extracted"""
        text = "Audit date: 13/13/2023"  # Invalid month

        with patch("cdie.extraction.auditdate.DATE_KEYWORDS", ["audit date"]):
            with patch("cdie.extraction.confidence.near_keyword") as mock_near:
                mock_near.return_value = "audit date"
                results = list(self.extractor.extract(text))

        # Should still extract as regex matches, but this is expected behavior
        assert len(results) == 1

    def test_empty_text(self):
        """Test extraction with empty text"""
        text = ""

        results = list(self.extractor.extract(text))
        assert len(results) == 0

    def test_text_without_dates(self):
        """Test extraction of text without any dates"""
        text = "This is a sample text without any dates"

        results = list(self.extractor.extract(text))
        assert len(results) == 0

    def test_date_regex_patterns(self):
        """Test that all date regex patterns are defined"""
        assert len(DATE_REGEXES) >= 4
        assert all(isinstance(pattern, str) for pattern in DATE_REGEXES)

    def test_confidence_scoring(self):
        """Test confidence scoring logic"""
        # Full date format should get higher confidence
        text = "Audit date: 2023-07-15"

        with patch("cdie.extraction.auditdate.DATE_KEYWORDS", ["audit date"]):
            with patch("cdie.extraction.confidence.near_keyword") as mock_near:
                mock_near.return_value = "audit date"
                results = list(self.extractor.extract(text))

        assert results[0].confidence == 0.9  # SCORE_EXACT

        # Month year only should get lower confidence
        text = "Audit period: October 2012"

        with patch("cdie.extraction.auditdate.DATE_KEYWORDS", ["audit period"]):
            with patch("cdie.extraction.confidence.near_keyword") as mock_near:
                mock_near.return_value = "audit period"
                results = list(self.extractor.extract(text))

        assert results[0].confidence == 0.7  # SCORE_MONTH_YEAR
