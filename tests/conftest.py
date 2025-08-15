"""
Common test fixtures and configuration for the cdie test suite.
"""

from unittest.mock import Mock

import pytest
from spacy.language import Language


@pytest.fixture
def mock_nlp():
    """Create a mock spaCy NLP object for testing."""
    mock = Mock(spec=Language)
    return mock


@pytest.fixture
def mock_spacy_doc():
    """Create a mock spaCy document for testing."""
    mock_doc = Mock()
    mock_doc.ents = []
    return mock_doc


@pytest.fixture
def mock_spacy_entity():
    """Create a mock spaCy entity for testing."""
    mock_ent = Mock()
    mock_ent.label_ = "PERSON"
    mock_ent.text = "Test Entity"
    mock_ent.sent.text = "Test sentence with Test Entity"
    return mock_ent


@pytest.fixture
def sample_audit_text():
    """Sample audit text for testing."""
    return """
    Audit Report
    
    Audit Date: 2023-07-15
    Auditor: John Doe
    Auditee: ABC Manufacturing Ltd
    
    Findings:
    - Noncompliance found in safety procedures
    - Finding: Inadequate documentation
    - Issue: Missing safety equipment
    
    The audit was conducted at the ABC Manufacturing Ltd factory facility.
    """
