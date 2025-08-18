from unittest.mock import Mock, patch

import pytest

from cdie.extraction.suppliers import (
    COMPANY_NAME,
    ORG_KEYWORDS,
    SupplierExtractor,
)


class TestOrganizationExtractor:
    """Test cases for OrganizationExtractor"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_nlp = Mock()
        self.extractor = SupplierExtractor(self.mock_nlp)

    def test_extract_org_entity_with_keyword(self):
        """Test extraction of organization entity with keyword"""
        # Mock spaCy document and entities
        mock_ent = Mock()
        mock_ent.label_ = "ORG"
        mock_ent.text = "ABC Manufacturing"
        mock_ent.sent.text = "ABC Manufacturing factory was audited"

        mock_doc = Mock()
        mock_doc.ents = [mock_ent]

        self.mock_nlp.return_value = mock_doc

        text = "ABC Manufacturing factory was audited"

        with patch("cdie.extraction.confidence.near_keyword") as mock_near:
            mock_near.return_value = "factory"
            with patch("cdie.extraction.confidence.boost_confidence") as mock_boost:
                mock_boost.return_value = 0.9
                results = list(self.extractor.extract(text))

        assert len(results) == 1
        assert results[0].name == "ABC Manufacturing"
        assert results[0].confidence == 0.9

    def test_extract_regex_organization(self):
        """Test extraction of organization using regex pattern"""
        text = "ABC Manufacturing Ltd factory was audited"

        # Mock spaCy with no entities
        mock_doc = Mock()
        mock_doc.ents = []
        self.mock_nlp.return_value = mock_doc

        with patch("cdie.extraction.confidence.near_keyword") as mock_near:
            mock_near.return_value = "factory"
            results = list(self.extractor.extract(text))

        assert len(results) == 1
        assert results[0].name == "ABC Manufacturing Ltd"
        assert results[0].confidence == 0.85

    def test_extract_multiple_organizations(self):
        """Test extraction when multiple organizations are found"""
        # Mock spaCy document and entities
        mock_ent1 = Mock()
        mock_ent1.label_ = "ORG"
        mock_ent1.text = "ABC Manufacturing"
        mock_ent1.sent.text = "ABC Manufacturing factory was audited"

        mock_ent2 = Mock()
        mock_ent2.label_ = "ORG"
        mock_ent2.text = "XYZ Corp"
        mock_ent2.sent.text = "XYZ Corp facility was inspected"

        mock_doc = Mock()
        mock_doc.ents = [mock_ent1, mock_ent2]

        self.mock_nlp.return_value = mock_doc

        text = "ABC Manufacturing factory was audited. XYZ Corp facility was inspected."

        with patch("cdie.extraction.confidence.near_keyword") as mock_near:
            mock_near.return_value = "factory"
            with patch("cdie.extraction.confidence.boost_confidence") as mock_boost:
                mock_boost.return_value = 0.9
                results = list(self.extractor.extract(text))

        # Should return the one with highest confidence
        assert len(results) == 1
        assert results[0].name == "ABC Manufacturing"

    def test_no_organization_found(self):
        """Test when no organization is found"""
        # Mock spaCy document with no entities
        mock_doc = Mock()
        mock_doc.ents = []

        self.mock_nlp.return_value = mock_doc

        text = "This is a sample text without any organizations"

        results = list(self.extractor.extract(text))
        assert len(results) == 0

    def test_org_not_near_keyword(self):
        """Test when organization entity is not near keyword"""
        # Mock spaCy document and entities
        mock_ent = Mock()
        mock_ent.label_ = "ORG"
        mock_ent.text = "ABC Manufacturing"
        mock_ent.sent.text = "ABC Manufacturing is a company"

        mock_doc = Mock()
        mock_doc.ents = [mock_ent]

        self.mock_nlp.return_value = mock_doc

        text = "ABC Manufacturing is a company"

        with patch("cdie.extraction.confidence.near_keyword") as mock_near:
            mock_near.return_value = None
            results = list(self.extractor.extract(text))

        assert len(results) == 0

    def test_non_org_entity(self):
        """Test when entity is not an organization"""
        # Mock spaCy document and entities
        mock_ent = Mock()
        mock_ent.label_ = "PERSON"
        mock_ent.text = "John Doe"
        mock_ent.sent.text = "John Doe works at the factory"

        mock_doc = Mock()
        mock_doc.ents = [mock_ent]

        self.mock_nlp.return_value = mock_doc

        text = "John Doe works at the factory"

        with patch("cdie.extraction.confidence.near_keyword") as mock_near:
            mock_near.return_value = "factory"
            results = list(self.extractor.extract(text))

        assert len(results) == 0

    def test_regex_organization_variants(self):
        """Test regex extraction with various organization suffixes"""
        test_cases = [
            ("ABC Manufacturing Ltd", "factory"),
            ("XYZ Corporation", "facility"),
            ("DEF Company", "mill"),
            ("GHI Inc", "plant"),
            ("JKL Co.", "manufacturer"),
        ]

        for org_name, keyword in test_cases:
            text = f"{org_name} {keyword} was audited"

            # Mock spaCy with no entities
            mock_doc = Mock()
            mock_doc.ents = []
            self.mock_nlp.return_value = mock_doc

            with patch("cdie.extraction.confidence.near_keyword") as mock_near:
                mock_near.return_value = keyword
                results = list(self.extractor.extract(text))

            assert len(results) == 1
            assert results[0].name == org_name
            assert results[0].confidence == 0.85

    def test_confidence_boost_calculation(self):
        """Test confidence boost calculation for NER entities"""
        # Mock spaCy document and entities
        mock_ent = Mock()
        mock_ent.label_ = "ORG"
        mock_ent.text = "ABC Manufacturing"
        mock_ent.sent.text = "ABC Manufacturing factory was audited"

        mock_doc = Mock()
        mock_doc.ents = [mock_ent]

        self.mock_nlp.return_value = mock_doc

        text = "ABC Manufacturing factory was audited"

        with patch("cdie.extraction.confidence.near_keyword") as mock_near:
            mock_near.return_value = "factory"
            with patch("cdie.extraction.confidence.boost_confidence") as mock_boost:
                mock_boost.return_value = 0.9
                results = list(self.extractor.extract(text))

        # Verify boost_confidence was called with correct parameters
        mock_boost.assert_called_with(0.7, 0.2)

    def test_empty_text(self):
        """Test extraction with empty text"""
        text = ""

        results = list(self.extractor.extract(text))
        assert len(results) == 0

    def test_text_without_keywords(self):
        """Test extraction of text without keywords"""
        text = "This is a sample text without any factory keywords"

        results = list(self.extractor.extract(text))
        assert len(results) == 0

    def test_org_keywords_defined(self):
        """Test that organization keywords are properly defined"""
        assert len(ORG_KEYWORDS) > 0
        assert all(isinstance(kw, str) for kw in ORG_KEYWORDS)
        assert "factory" in ORG_KEYWORDS
        assert "facility" in ORG_KEYWORDS
        assert "mill" in ORG_KEYWORDS

    def test_regex_pattern_defined(self):
        """Test that regex pattern is properly defined"""
        assert isinstance(COMPANY_NAME, str)
        assert len(COMPANY_NAME) > 0

    def test_ner_vs_regex_priority(self):
        """Test that NER entities take priority over regex matches"""
        # Mock spaCy document and entities
        mock_ent = Mock()
        mock_ent.label_ = "ORG"
        mock_ent.text = "ABC Manufacturing"
        mock_ent.sent.text = "ABC Manufacturing Ltd factory was audited"

        mock_doc = Mock()
        mock_doc.ents = [mock_ent]

        self.mock_nlp.return_value = mock_doc

        text = "ABC Manufacturing Ltd factory was audited"

        with patch("cdie.extraction.confidence.near_keyword") as mock_near:
            mock_near.return_value = "factory"
            with patch("cdie.extraction.confidence.boost_confidence") as mock_boost:
                mock_boost.return_value = 0.9
                results = list(self.extractor.extract(text))

        # Should prefer NER entity over regex match
        assert len(results) == 1
        assert results[0].name == "ABC Manufacturing"  # NER entity
        assert results[0].confidence == 0.9  # NER confidence

    def test_multiple_regex_matches(self):
        """Test handling of multiple regex matches"""
        text = "ABC Manufacturing Ltd and XYZ Corporation Ltd factory was audited"

        # Mock spaCy with no entities
        mock_doc = Mock()
        mock_doc.ents = []
        self.mock_nlp.return_value = mock_doc

        with patch("cdie.extraction.confidence.near_keyword") as mock_near:
            mock_near.return_value = "factory"
            results = list(self.extractor.extract(text))

        # Should return the first match
        assert len(results) == 1
        assert results[0].name == "ABC Manufacturing Ltd"

    def test_organization_with_ampersand(self):
        """Test extraction of organization with ampersand"""
        text = "Smith & Jones Manufacturing Ltd factory was audited"

        # Mock spaCy with no entities
        mock_doc = Mock()
        mock_doc.ents = []
        self.mock_nlp.return_value = mock_doc

        with patch("cdie.extraction.confidence.near_keyword") as mock_near:
            mock_near.return_value = "factory"
            list(self.extractor.extract(text))  # Just call to verify no errors
