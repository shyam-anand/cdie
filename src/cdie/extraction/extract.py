import logging
import re
from pathlib import Path
from typing import Generator

import pdfplumber
import spacy
from pdfplumber.page import Page
from pdfplumber.table import Table
from spacy.language import Language

from cdie import config
from cdie.extraction.extractors import extractor
from cdie.extraction.extractors.auditdate import AuditDateExtractor
from cdie.extraction.extractors.auditor import AuditorExtractor
from cdie.extraction.extractors.findings import FindingsExtractor
from cdie.extraction.extractors.suppliers import SupplierExtractor

logger = logging.getLogger(__name__)

RESOURCE_DIR = config.RESOURCES_ROOT / "files"
NON_LATIN_RE = re.compile(r"[^\x00-\x7f]")

nlp: Language | None = None


def load_nlp():
    global nlp
    if nlp is None:
        # enable only Named Entity Recognition
        nlp = spacy.load("en_core_web_sm", exclude=["attribute_ruler", "lemmatizer"])
        nlp.add_pipe("sentencizer")
    return nlp


def extract_tables_from_page(tables: list[Table]) -> Generator[list[str], None, None]:
    for table in tables:
        table_rows = table.extract()
        row_count = 0
        for row in table_rows:
            row_count += 1
            cells = [cell for cell in row if cell and cell.strip()]
            if cells:
                yield cells


def extract_text_from_page(page: Page, remove_non_latin: bool = True) -> Generator[str, None, None]:
    logger.info(f"On page {page.page_number}")
    # images = page.images
    # logger.info(f"Ignoring {len(images)} images")

    # if tables := page.find_tables():
    #     for row in extract_tables_from_page(tables):
    #         if row:
    #             logger.info("\t".join([f"[{cell}]" for cell in row]))

    extracted_text = page.extract_text()
    text = NON_LATIN_RE.sub("", extracted_text) if remove_non_latin else extracted_text
    logger.info(f"Extracted text: {text}")
    yield text


def extract_text_from_pdf(file_path: Path) -> Generator[str, None, None]:
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                yield from extract_text_from_page(page)

    except Exception as e:
        logger.error(f"Error extracting text from {file_path}: {e}")


def extract_info(
    file_name: str,
    extract_types: list[str] = ["auditor", "date", "factory", "findings"],
) -> Generator[extractor.Extracted, None, None]:
    file_path = RESOURCE_DIR / file_name
    if not file_path.exists():
        raise FileNotFoundError(f"File {file_path} not found")
    if not file_path.suffix == ".pdf":
        raise ValueError(f"File {file_path} is not a PDF file")

    nlp = load_nlp()
    logger.info(f"nlp loaded: {nlp}")

    for text in extract_text_from_pdf(file_path):
        if not text:
            continue
        doc = nlp(text)
        logger.info(f"Processing text: {doc.text}")
        if "auditor" in extract_types:
            yield from AuditorExtractor(nlp).extract(doc)

        if "date" in extract_types:
            yield from AuditDateExtractor(nlp).extract(doc)

        if "factory" in extract_types:
            yield from SupplierExtractor(nlp).extract(doc)

        if "findings" in extract_types:
            yield from FindingsExtractor(nlp).extract(doc)
