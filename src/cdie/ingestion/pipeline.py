import logging
import pathlib
from typing import Any, Literal

import spacy
from spacy.language import Language

from cdie import config
from cdie.extraction.auditdate import AuditDateExtractor
from cdie.extraction.auditor import AuditorExtractor
from cdie.extraction.findings import FindingsExtractor
from cdie.extraction.suppliers import SupplierExtractor
from cdie.ingestion import pdfparser
from cdie.reports import reportgenerator
from cdie.storage import jsonfilestore

logger = logging.getLogger(__name__)


INGESTION_DATA_DIR = config.DATA_ROOT / "ingestion"

ExtractorType = Literal["auditor", "date", "supplier", "findings"]

# Mapping of extractor types to their classes
EXTRACTOR_CLASSES = {
    "auditor": AuditorExtractor,
    "date": AuditDateExtractor,
    "supplier": SupplierExtractor,
    "findings": FindingsExtractor,
}


nlp: Language | None = None


def get_nlp() -> Language:
    global nlp
    if nlp is None:
        # enable only Named Entity Recognition
        nlp = spacy.load("en_core_web_sm", exclude=["attribute_ruler", "lemmatizer"])
        nlp.add_pipe("sentencizer")
        logger.info("nlp loaded")
    return nlp


def _get_storage() -> jsonfilestore.JsonFileStore:
    return jsonfilestore.JsonFileStore(INGESTION_DATA_DIR)


class IngestionPipeline:
    def __init__(self, storage: jsonfilestore.JsonFileStore | None = None):
        self._storage = storage or _get_storage()

    def read_extracted(self, request_id: str, type: str) -> list[dict[str, Any]]:
        return self._storage.read_list(request_id, type)

    def _set_status(self, request_id: str, status: str):
        self._storage.write(request_id, "status", {"status": status})

    def run(
        self,
        file_path: pathlib.Path,
        request_id: str,
        extract_types: list[ExtractorType],
        generate_report: bool = True,
    ) -> None:
        logger.info(f"Starting: {request_id}")
        self._set_status(request_id, "running")

        nlp = get_nlp()
        pdf_parser = pdfparser.PdfParser()
        extractors = [EXTRACTOR_CLASSES[extract_type](nlp) for extract_type in extract_types]

        for text in pdf_parser.parse(file_path):
            doc = nlp(text)
            for info_extractor in extractors:
                for info in info_extractor.extract(doc):
                    self._storage.append(request_id, info.__class__.__name__, info.model_dump())
        logger.info(f"Extraction completed for {request_id}")

        if generate_report:
            report_generator = reportgenerator.ReportGenerator(request_id)
            report_generator.finalize()

        self._set_status(request_id, "completed")
        logger.info(f"Completed: {request_id}")


def get_status(request_id: str) -> str | None:
    status_dict = _get_storage().read(request_id, "status")
    if status_dict and isinstance(status_dict, dict):
        return status_dict["status"]
    return None


def run(
    file_path: pathlib.Path,
    request_id: str,
    extract_types: list[ExtractorType],
    generate_report: bool = True,
) -> None:
    ingestion_pipeline = IngestionPipeline(_get_storage())
    ingestion_pipeline.run(file_path, request_id, extract_types, generate_report)
