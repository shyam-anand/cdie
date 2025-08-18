import argparse
import logging
from typing import Any, Callable, Iterable

from cdie import config
from cdie.extraction import extractor
from cdie.models import audit
from cdie.storage import jsonfilestore

logger = logging.getLogger(__name__)

REPORTS = config.DATA_ROOT / "reports"
INGESTION = config.DATA_ROOT / "ingestion"


DictToExtracted = Callable[[dict[str, Any]], extractor.T]

CONFIDENCE_THRESHOLD = config.get_config("confidence_threshold") or 0.60

argparser = argparse.ArgumentParser()
argparser.add_argument("--confidence-threshold", type=float, default=CONFIDENCE_THRESHOLD)
args, _ = argparser.parse_known_args()

_confidence_threshold = args.confidence_threshold


class ReportGenerator:
    """
    After extraction, this class creates the audit report by getting the best candidates for
    auditor and audit date, and all candidates with confidence above threshold for suppliers and
    findings.

    The report is saved to the reports directory.
    """

    def __init__(
        self,
        request_id: str,
        confidence_threshold: float = _confidence_threshold,
    ):
        self._confidence_threshold = confidence_threshold
        self._request_id = request_id

        self._storage = jsonfilestore.JsonFileStore(REPORTS, create_dir=True)

    def save_report(self, report: audit.AuditReport | None = None):
        if report is None:
            logger.warning("No report provided, skipping save")
            return
        self._storage.write(self._request_id, "report", report.model_dump())
        logger.info(f"Report saved for {self._request_id}")

    def read_candidates(self, type: str) -> list[dict[str, Any]]:
        ingestion_storage = jsonfilestore.JsonFileStore(INGESTION)
        return ingestion_storage.read_list(self._request_id, type)

    def _get_candidates_above_threshold(
        self, type: str, mapper: DictToExtracted[extractor.T]
    ) -> Iterable[extractor.T]:
        """Returns all candidates with confidence above threshold."""
        return filter(
            lambda x: x.confidence >= self._confidence_threshold,
            map(mapper, self.read_candidates(type)),
        )

    def _get_best_candidate(
        self, type: str, mapper: DictToExtracted[extractor.T]
    ) -> extractor.T | None:
        """Returns the best candidate by confidence."""
        candidates = list(self._get_candidates_above_threshold(type, mapper))
        if not candidates:
            return None
        return max(
            candidates,
            key=lambda x: x.confidence,
        )

    def _get_auditor(self) -> audit.Auditor | None:
        """
        Returns the best auditor candidate by confidence, and attempts to fill in missing
        fields.
        """
        candidates = list(
            self._get_candidates_above_threshold("Auditor", audit.Auditor.model_validate)
        )
        candidates.sort(key=lambda x: x.confidence)
        if not candidates:
            return None
        best_candidate = candidates.pop()

        # Attempt to fill in missing fields
        while candidates and not (best_candidate.name and best_candidate.organization):
            candidate = candidates.pop()
            if not best_candidate.name:
                if not candidate.name:
                    continue
                best_candidate.name = candidate.name
            if not best_candidate.organization:
                if not candidate.organization:
                    continue
                best_candidate.organization = candidate.organization
            best_candidate.confidence = (best_candidate.confidence + candidate.confidence) / 2

        return best_candidate

    def finalize(self) -> audit.AuditReport:
        """
        Creates the report by getting the best candidates for auditor and audit date, and all
        candidates with confidence above threshold for suppliers and findings.
        """
        logger.info(f"Finalizing report for {self._request_id}")
        auditor = self._get_auditor()
        audit_date = self._get_best_candidate("AuditDate", audit.AuditDate.model_validate)
        suppliers = self._get_candidates_above_threshold("Supplier", audit.Supplier.model_validate)
        findings = self._get_candidates_above_threshold("Finding", audit.Finding.model_validate)
        report = audit.AuditReport(
            auditor=auditor,  # type: ignore
            audit_date=audit_date,  # type: ignore
            suppliers=suppliers,  # type: ignore
            findings=findings,  # type: ignore
        )
        self.save_report(report)
        logger.info(f"Report finalized for {self._request_id}")
        return report


def get_report(request_id: str) -> audit.AuditReport | None:
    """Returns the report for the given request ID."""
    report_dict = jsonfilestore.JsonFileStore(REPORTS).read(request_id, "report")
    if report_dict and isinstance(report_dict, dict):
        return audit.AuditReport.model_validate(report_dict)
    return None
