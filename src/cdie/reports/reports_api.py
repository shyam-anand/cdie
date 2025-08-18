import logging

from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from cdie.ingestion import pipeline as ingestion_pipeline

from cdie.reports import reportgenerator
from cdie.models import audit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


class ReportResponse(BaseModel):
    status: str
    report: audit.AuditReport | None = None


@router.get(
    "/{request_id}",
    response_model=ReportResponse,
    response_model_exclude_none=True,
)
async def get(request_id: str):
    if status := ingestion_pipeline.get_status(request_id):
        response = ReportResponse(status=status)
        if report := reportgenerator.get_report(request_id):
            response.report = report
        return response

    raise HTTPException(status_code=404, detail="request_id not found")
