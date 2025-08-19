import logging
import re
from typing import Iterable

import pandas as pd
from spacy.language import Language
from spacy.tokens import Doc
from spacy.tokens.span import Span

from cdie.extraction.confidence import Confidence, ConfidenceCriteria
from cdie.extraction.extractor import Extractor
from cdie.extraction.textutils import keywords
from cdie.ingestion.pdfparser import PageData
from cdie.models import audit

logger = logging.getLogger(__name__)


FINDING_KEYWORDS = keywords.load_keywords("findings")

SEVERITY_KEYWORDS = {
    "critical": ["critical", "severe", "major", "serious", "significant"],
    "high": ["high", "important", "substantial", "considerable"],
    "medium": ["moderate", "medium", "notable", "material"],
    "low": ["minor", "low", "small", "minimal"],
}

FINDINGS_SECTIONS = [
    "findings",
    "observations",
    "recommendations",
    "issues",
    "deficiencies",
    "violations",
    "exceptions",
    "concerns",
    "audit results",
    "inspection results",
    "compliance review",
]

STRUCTURED_PATTERNS = [
    re.compile(pattern, re.IGNORECASE | re.DOTALL)
    for pattern in [
        r"Finding\s+#?\d+:?\s*(.+?)(?=Finding\s+#?\d+|$)",
        r"Issue\s+#?\d+:?\s*(.+?)(?=Issue\s+#?\d+|$)",
        r"Observation\s+#?\d+:?\s*(.+?)(?=Observation\s+#?\d+|$)",
        r"Deficiency\s+#?\d+:?\s*(.+?)(?=Deficiency\s+#?\d+|$)",
        r"\d+\.\s+(.+?)(?=\d+\.|$)",
    ]
]
FINDINGS_CATEGORIES = {
    "financial": ["financial", "money", "payment", "invoice", "accounting", "budget"],
    "safety": ["safety", "hazard", "accident", "injury", "risk", "dangerous"],
    "regulatory": ["regulation", "law", "legal", "compliance", "requirement", "standard"],
    "operational": ["process", "procedure", "operation", "workflow", "system"],
    "documentation": ["document", "record", "report", "file", "paperwork"],
    "quality": ["quality", "defect", "standard", "specification", "performance"],
    "security": ["security", "access", "authorization", "password", "breach"],
    "environmental": ["environment", "pollution", "waste", "emission", "green"],
}


class FindingsExtractor(Extractor[audit.Finding]):
    def __init__(self, nlp: Language):
        confidence = Confidence()
        confidence.set_weight(ConfidenceCriteria.NEAR_KEYWORD, 0.5)
        # No regex or NER for findings
        confidence.set_weight(ConfidenceCriteria.REGEX_MATCH, 0.0)
        confidence.set_weight(ConfidenceCriteria.NER_MATCH, 0.0)

        super().__init__(nlp, confidence=confidence)
        self.max_distance = 700

        self._findings_count = 1

    def categorize_finding(self, text: str) -> str:
        """Categorize the finding based on content"""
        text_lower = text.lower()

        for category, category_keywords in FINDINGS_CATEGORIES.items():
            if any(keyword in text_lower for keyword in category_keywords):
                return category

        return "general"

    def determine_severity(self, text: str) -> str:
        """Determine the severity level of the finding"""
        text_lower = text.lower()

        for severity, severity_keywords in SEVERITY_KEYWORDS.items():
            if any(keyword in text_lower for keyword in severity_keywords):
                return severity

        return "medium"  # default

    def calculate_confidence(self, text: str, method: str, keyword_count: int = 0) -> float:
        """Calculate confidence score for the finding

        Findings uses a different confidence logic that the others, because findings are
        much less structured.
        """
        base_confidence = {"structured": 0.9, "table": 0.8, "nlp": 0.6}.get(method, 0.5)

        # Adjust based on keyword density
        if keyword_count > 0:
            keyword_bonus = min(keyword_count * 0.1, 0.3)
            base_confidence = min(base_confidence + keyword_bonus, 1.0)

        # Adjust based on text length (longer texts often more reliable)
        if len(text) > 100:
            base_confidence = min(base_confidence + 0.1, 1.0)
        elif len(text) < 30:
            base_confidence = max(base_confidence - 0.2, 0.1)

        return round(base_confidence, 4)

    def identify_finding_sections(self, text: str) -> list[str]:
        """Identify sections likely to contain findings"""
        sections: list[str] = []
        lines = text.split("\n")
        current_section = ""
        in_finding_section = False

        for line in lines:
            line_lower = line.lower().strip()

            # Check if this line is a section header
            if any(section in line_lower for section in FINDINGS_SECTIONS):
                in_finding_section = True
                if current_section:
                    sections.append(current_section)
                current_section = line + "\n"
            elif in_finding_section:
                current_section += line + "\n"

                # Stop if we hit a new major section (all caps, short line)
                if (
                    line.isupper()
                    and len(line) < 50
                    and not any(keyword in line_lower for keyword in FINDING_KEYWORDS)
                ):
                    sections.append(current_section)
                    current_section = ""
                    in_finding_section = False

        if current_section:
            sections.append(current_section)

        return sections

    def extract_context(
        self, full_text: str, start: int, end: int, context_chars: int = 200
    ) -> str:
        """Extract context text around a finding"""
        context_start = max(0, start - context_chars)
        context_end = min(len(full_text), end + context_chars)

        context = full_text[context_start:context_end].strip()
        return re.sub(r"\s+", " ", context)

    def extract_from_structured_text(self, text: str, page_number: int) -> Iterable[audit.Finding]:
        """Extract findings using structured patterns"""

        for pattern in STRUCTURED_PATTERNS:
            matches = pattern.finditer(text)

            for match in matches:
                finding_text = match.group(1).strip()

                # Skip if too short or likely not a finding
                if len(finding_text) < 20:
                    continue

                # Clean up the text
                finding_text = re.sub(r"\s+", " ", finding_text)

                # Determine category and severity
                category = self.categorize_finding(finding_text)
                severity = self.determine_severity(finding_text)
                confidence = self.calculate_confidence(finding_text, "structured")
                context = self.extract_context(text, match.start(), match.end())

                self._findings_count += 1
                finding = audit.Finding(
                    id=f"F{self._findings_count:03d}",
                    text=finding_text,
                    category=category,
                    severity=severity,
                    confidence=confidence,
                    context={"context": context, "page_number": page_number},
                    source_method="structured_pattern",
                )

                yield finding

    def extract_sentence_context(self, doc: Doc, target_sentence: Span) -> str:
        """Extract context around a sentence using spaCy"""
        sentences = list(doc.sents)
        target_idx = -1

        for i, sent in enumerate(sentences):
            if sent == target_sentence:
                target_idx = i
                break

        if target_idx == -1:
            return target_sentence.text

        # Get previous and next sentence
        context_sents: list[str] = []
        if target_idx > 0:
            context_sents.append(sentences[target_idx - 1].text)
        context_sents.append(target_sentence.text)
        if target_idx < len(sentences) - 1:
            context_sents.append(sentences[target_idx + 1].text)

        return " ".join(context_sents)

    def extract_with_nlp(self, doc: Doc, page_number: int) -> Iterable[audit.Finding]:
        for sentence in doc.sents:
            sentence_text = sentence.text.strip()
            if not sentence_text:
                continue

            keyword_count = sum(
                1 for keyword in FINDING_KEYWORDS if keyword in sentence_text.lower()
            )

            if keyword_count > 0 and len(sentence_text) > 30:
                context = self.extract_sentence_context(doc, sentence)
                category = self.categorize_finding(sentence_text)
                severity = self.determine_severity(sentence_text)
                confidence = self.calculate_confidence(sentence_text, "nlp", keyword_count)

                self._findings_count += 1
                yield audit.Finding(
                    id=f"F{self._findings_count:03d}",
                    text=sentence_text,
                    category=category,
                    severity=severity,
                    confidence=confidence,
                    context={"context": context, "page_number": page_number},
                    source_method="nlp_analysis",
                )

    def extract_from_tables(
        self, tables: list[list[list[str | None]]], page_number: int
    ) -> Iterable[audit.Finding]:
        """Extract findings from tabular data"""

        for table in tables:
            if not table:
                continue

            try:
                # Convert table to DataFrame for easier processing
                df = pd.DataFrame(table[1:], columns=table[0])

                # Look for columns that might contain findings
                finding_columns: list[str] = []
                for col in df.columns:
                    if col and any(
                        keyword in str(col).lower()
                        for keyword in FINDING_KEYWORDS + FINDINGS_SECTIONS
                    ):
                        finding_columns.append(col)

                # Extract findings from relevant columns
                for col in finding_columns:
                    # Iterate through all non-null values in the current column
                    # dropna() removes empty values to avoid processing empty cells
                    for idx, value in df[col].dropna().items():  # type: ignore
                        # Filter for relevant text content - skip short entries that are unlikely
                        # to be meaningful findings
                        if isinstance(value, str) and len(value) > 20:
                            category = self.categorize_finding(value)
                            severity = self.determine_severity(value)
                            confidence = self.calculate_confidence(value, "table")

                            # Build context by collecting data from other columns in the same row
                            # This provides additional information about the finding
                            # (e.g., department, date, auditor)
                            context_parts: list[str] = []
                            for other_col in df.columns:
                                # Filter for non-null values
                                if other_col != col and pd.notna(
                                    df.iloc[idx][other_col]  # type: ignore
                                ):
                                    # Format as "column_name: value" for readability
                                    context_parts.append(f"{other_col}: {df.iloc[idx][other_col]}")  # type: ignore

                            context = " | ".join(context_parts)

                            self._findings_count += 1
                            yield audit.Finding(
                                id=f"F{self._findings_count:03d}",
                                text=value,
                                category=category,
                                severity=severity,
                                confidence=confidence,
                                context={"context": context, "page_number": page_number},
                                source_method="table_extraction",
                            )

            except Exception as e:
                logger.warning(f"Error processing table: {e}")

    def extract(self, page_data: PageData) -> Iterable[audit.Finding]:
        yield from self.extract_from_structured_text(page_data.text, page_data.page_number)
        yield from self.extract_with_nlp(self.nlp(page_data.text), page_data.page_number)
        if page_data.tables:
            yield from self.extract_from_tables(page_data.tables, page_data.page_number)
