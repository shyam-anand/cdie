from unittest.mock import Mock, patch

import pytest

from cdie.extraction.extractors.auditor import AUDITOR_KEYWORDS, AuditorExtractor


class TestAuditorExtractor:
    """Test cases for AuditorExtractor"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_nlp = Mock()
        self.extractor = AuditorExtractor(self.mock_nlp)

    def test_extract_person_with_keyword(self):
        """Test extraction of person entity with keyword"""
        # Mock spaCy document and entities
        mock_ent = Mock()
        mock_ent.label_ = "PERSON"
        mock_ent.text = "John Doe"
        mock_ent.sent.text = "Audit conducted by John Doe"

        mock_doc = Mock()
        mock_doc.ents = [mock_ent]

        self.mock_nlp.return_value = mock_doc

        text = "Audit conducted by John Doe"

        with patch("cdie.extraction.confidence.near_keyword") as mock_near:
            mock_near.return_value = "auditor"
            with patch("cdie.extraction.confidence.boost_confidence") as mock_boost:
                mock_boost.return_value = 0.9
                results = list(self.extractor.extract(text))

        assert len(results) == 1
        assert results[0].name == "John Doe"
        assert results[0].confidence == 0.9

    def test_extract_multiple_persons(self):
        """Test extraction of multiple person entities"""
        # Mock spaCy document and entities
        mock_ent1 = Mock()
        mock_ent1.label_ = "PERSON"
        mock_ent1.text = "John Doe"
        mock_ent1.sent.text = "Audit conducted by John Doe and Jane Smith"

        mock_ent2 = Mock()
        mock_ent2.label_ = "PERSON"
        mock_ent2.text = "Jane Smith"
        mock_ent2.sent.text = "Audit conducted by John Doe and Jane Smith"

        mock_doc = Mock()
        mock_doc.ents = [mock_ent1, mock_ent2]

        self.mock_nlp.return_value = mock_doc

        text = "Audit conducted by John Doe and Jane Smith"

        with patch("cdie.extraction.confidence.near_keyword") as mock_near:
            mock_near.return_value = "auditor"
            with patch("cdie.extraction.confidence.boost_confidence") as mock_boost:
                mock_boost.return_value = 0.9
                results = list(self.extractor.extract(text))

        assert len(results) == 2
        assert results[0].name == "John Doe"
        assert results[1].name == "Jane Smith"

    def test_no_person_entity_found(self):
        """Test when no person entity is found"""
        # Mock spaCy document with no entities
        mock_doc = Mock()
        mock_doc.ents = []

        self.mock_nlp.return_value = mock_doc

        text = "Audit conducted by Compliance Manager"

        with patch("cdie.extraction.confidence.near_keyword") as mock_near:
            mock_near.return_value = "auditor"
            results = list(self.extractor.extract(text))

        assert len(results) == 0

    def test_person_not_near_keyword(self):
        """Test when person entity is not near keyword"""
        # Mock spaCy document and entities
        mock_ent = Mock()
        mock_ent.label_ = "PERSON"
        mock_ent.text = "John Doe"
        mock_ent.sent.text = "John Doe works in accounting"

        mock_doc = Mock()
        mock_doc.ents = [mock_ent]

        self.mock_nlp.return_value = mock_doc

        text = "John Doe works in accounting"

        with patch("cdie.extraction.confidence.near_keyword") as mock_near:
            mock_near.return_value = None
            results = list(self.extractor.extract(text))

        assert len(results) == 0

    def test_non_person_entity(self):
        """Test when entity is not a person"""
        # Mock spaCy document and entities
        mock_ent = Mock()
        mock_ent.label_ = "ORG"
        mock_ent.text = "ABC Company"
        mock_ent.sent.text = "Audit conducted by ABC Company"

        mock_doc = Mock()
        mock_doc.ents = [mock_ent]

        self.mock_nlp.return_value = mock_doc

        text = "Audit conducted by ABC Company"

        with patch("cdie.extraction.confidence.near_keyword") as mock_near:
            mock_near.return_value = "auditor"
            results = list(self.extractor.extract(text))

        assert len(results) == 0

    def test_keyword_found_in_line(self):
        """Test when keyword is found in line"""
        # Mock spaCy document and entities
        mock_ent = Mock()
        mock_ent.label_ = "PERSON"
        mock_ent.text = "John Doe"
        mock_ent.sent.text = "Audit conducted by John Doe"

        mock_doc = Mock()
        mock_doc.ents = [mock_ent]

        self.mock_nlp.return_value = mock_doc

        text = "Audit conducted by John Doe"

        with patch("cdie.extraction.confidence.near_keyword") as mock_near:
            mock_near.side_effect = [
                "auditor",
                "auditor",
            ]  # First for line, second for sent
            with patch("cdie.extraction.confidence.boost_confidence") as mock_boost:
                mock_boost.return_value = 0.9
                results = list(self.extractor.extract(text))

        assert len(results) == 1
        assert results[0].name == "John Doe"

    def test_fallback_to_whole_document(self):
        """Test fallback to whole document when no candidates found"""
        # Mock spaCy document and entities
        mock_ent = Mock()
        mock_ent.label_ = "PERSON"
        mock_ent.text = "John Doe"
        mock_ent.sent.text = "John Doe conducted the audit"

        mock_doc = Mock()
        mock_doc.ents = [mock_ent]

        self.mock_nlp.return_value = mock_doc

        text = "Some text\nJohn Doe conducted the audit\nMore text"

        with patch("cdie.extraction.confidence.near_keyword") as mock_near:
            # First call returns None (no keyword in line), second returns keyword
            mock_near.side_effect = [None, "auditor"]
            with patch("cdie.extraction.confidence.boost_confidence") as mock_boost:
                mock_boost.return_value = 0.9
                results = list(self.extractor.extract(text))

        assert len(results) == 1
        assert results[0].name == "John Doe"

    def test_empty_text(self):
        """Test extraction with empty text"""
        text = ""

        results = list(self.extractor.extract(text))
        assert len(results) == 0

    def test_text_without_keywords(self):
        """Test extraction of text without keywords"""
        text = "This is a sample text without any auditor keywords"

        results = list(self.extractor.extract(text))
        assert len(results) == 0

    def test_auditor_keywords_defined(self):
        """Test that auditor keywords are properly defined"""
        assert len(AUDITOR_KEYWORDS) > 0
        assert all(isinstance(kw, str) for kw in AUDITOR_KEYWORDS)
        assert "auditor" in AUDITOR_KEYWORDS

    def test_confidence_boost_calculation(self):
        """Test confidence boost calculation"""
        # Mock spaCy document and entities
        mock_ent = Mock()
        mock_ent.label_ = "PERSON"
        mock_ent.text = "John Doe"
        mock_ent.sent.text = "Audit conducted by John Doe"

        mock_doc = Mock()
        mock_doc.ents = [mock_ent]

        self.mock_nlp.return_value = mock_doc

        text = "Audit conducted by John Doe"

        with patch("cdie.extraction.confidence.near_keyword") as mock_near:
            mock_near.return_value = "auditor"
            with patch("cdie.extraction.confidence.boost_confidence") as mock_boost:
                mock_boost.return_value = 0.9
                results = list(self.extractor.extract(text))

        # Verify boost_confidence was called with correct parameters
        mock_boost.assert_called_with(0.7, 0.2)

    def test_multiple_lines_with_keywords(self):
        """Test extraction from multiple lines with keywords"""
        # Mock spaCy document and entities
        mock_ent = Mock()
        mock_ent.label_ = "PERSON"
        mock_ent.text = "John Doe"
        mock_ent.sent.text = "Audit conducted by John Doe"

        mock_doc = Mock()
        mock_doc.ents = [mock_ent]

        self.mock_nlp.return_value = mock_doc

        text = "Audit conducted by John Doe\nInspection by Jane Smith"

        with patch("cdie.extraction.confidence.near_keyword") as mock_near:
            mock_near.return_value = "auditor"
            with patch("cdie.extraction.confidence.boost_confidence") as mock_boost:
                mock_boost.return_value = 0.9
                list(self.extractor.extract(text))  # Just call to verify no errors
