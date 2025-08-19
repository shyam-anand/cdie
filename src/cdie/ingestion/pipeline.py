import logging
import pathlib
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Literal

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


class Job(BaseModel):
    request_id: str
    status: str = "submitted"
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: datetime | None = None
    extract_types: list[ExtractorType]
    generate_report: bool


class IngestionPipeline:
    def __init__(self, storage: jsonfilestore.JsonFileStore | None = None):
        self._storage = storage or _get_storage()

    def _save_job_info(self, job: Job):
        self._storage.write(job.request_id, "job", job)

    def run(
        self,
        file_path: pathlib.Path,
        job: Job,
    ) -> None:
        logger.info(f"Starting: {job.request_id}")
        job.status = "running"
        self._save_job_info(job)

        nlp = get_nlp()
        pdf_parser = pdfparser.PdfParser()
        extractors = [EXTRACTOR_CLASSES[extract_type](nlp) for extract_type in job.extract_types]

        for page_data in pdf_parser.parse(file_path):
            for info_extractor in extractors:
                for info in info_extractor.extract(page_data):
                    if info.confidence > 0.0:
                        self._storage.append(job.request_id, info.__class__.__name__, info)
        logger.info(f"Extraction completed for {job.request_id}")

        if job.generate_report:
            report_generator = reportgenerator.ReportGenerator(job.request_id)
            report_generator.finalize()

        job.status = "completed"
        self._save_job_info(job)
        logger.info(f"Completed: {job.request_id}")


def get_status(request_id: str) -> str | None:
    job = _get_storage().read(request_id, "job", Job)
    if job:
        return job.status
    return None


def run(
    file_path: pathlib.Path,
    request_id: str,
    extract_types: list[ExtractorType],
    generate_report: bool = True,
) -> None:
    ingestion_pipeline = IngestionPipeline(_get_storage())
    ingestion_pipeline.run(
        file_path,
        Job(request_id=request_id, extract_types=extract_types, generate_report=generate_report),
    )
