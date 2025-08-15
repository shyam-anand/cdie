import json
import logging
from pathlib import Path
from typing import Any, Callable, Iterable

from cdie import config
from cdie.extraction.extractors import extractor
from cdie.models import audit

logger = logging.getLogger(__name__)

DATA_DIR = config.DATA_ROOT / "audit"

if not DATA_DIR.exists():
    DATA_DIR.mkdir(parents=True)


def save_candidate(candidate: extractor.Extracted, filename: str):
    json_line = candidate.model_dump_json()
    with open(DATA_DIR / filename, "a+") as file:
        file.write(json_line + "\n")


def read_candidates(filename: str) -> Iterable[dict[str, Any]]:
    with open(DATA_DIR / filename, "r") as file:
        for line in file:
            try:
                yield json.loads(line.strip())
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse line: {line.strip()}")
                raise e


def create_new_file(filename: str) -> Path:
    filepath = DATA_DIR / f"{filename}"
    if filepath.exists():
        with open(filepath, "r") as existing_file:
            with open(DATA_DIR / f"{filename}.old", "w+") as new_file:
                for line in existing_file:
                    new_file.write(line)
        filepath.unlink()
    else:
        logger.info(f"File {filepath} does not exist")
    return filepath


DictToExtracted = Callable[[dict[str, Any]], extractor.T]


class AuditReport:
    def __init__(self, source_file: str):
        self._source_file = source_file
        self._confidence_threshold = 0.60

        self._candidate_files: dict[str, Path] = {
            "Auditor": create_new_file(f"{self._source_file}_Auditor.jsonl"),
            "AuditDate": create_new_file(f"{self._source_file}_AuditDate.jsonl"),
            "Supplier": create_new_file(f"{self._source_file}_Supplier.jsonl"),
            "Finding": create_new_file(f"{self._source_file}_Finding.jsonl"),
        }

    def add_candidate(self, candidate: extractor.Extracted) -> None:
        candidate_type = candidate.__class__.__name__
        save_candidate(candidate, f"{self._source_file}_{candidate_type}.jsonl")

    def _get_candidates_above_threshold(
        self, candidate_file: str, mapper: DictToExtracted[extractor.T]
    ) -> Iterable[extractor.Extracted]:
        return list(
            filter(
                lambda x: x.confidence >= self._confidence_threshold,
                map(mapper, read_candidates(candidate_file)),
            )
        )

    def _get_best_candidate(
        self, candidate_file: str, mapper: DictToExtracted[extractor.T]
    ) -> extractor.Extracted:
        return max(
            self._get_candidates_above_threshold(candidate_file, mapper),
            key=lambda x: x.confidence,
        )

    def get_report(self) -> audit.Audit:
        auditor = self._get_best_candidate(
            f"{self._source_file}_Auditor.jsonl", audit.Auditor.model_validate
        )
        audit_date = self._get_best_candidate(
            f"{self._source_file}_AuditDate.jsonl", audit.AuditDate.model_validate
        )
        suppliers = self._get_candidates_above_threshold(
            f"{self._source_file}_Supplier.jsonl", audit.Supplier.model_validate
        )

        findings = self._get_candidates_above_threshold(
            f"{self._source_file}_Finding.jsonl", audit.Finding.model_validate
        )
        return audit.Audit(
            auditor=auditor,
            audit_date=audit_date,
            suppliers=suppliers,
            findings=findings,
        )
