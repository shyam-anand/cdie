import logging

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Query, UploadFile, status

from cdie.ingestion import file_uploader
from cdie.ingestion import pipeline as ingestion_pipeline
from cdie.reports import requestid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/", status_code=status.HTTP_202_ACCEPTED)
async def create(
    background_tasks: BackgroundTasks,
    upload_file: UploadFile = File(...),
    auditor: bool = Query(default=True),
    date: bool = Query(default=True),
    supplier: bool = Query(default=True),
    findings: bool = Query(default=True),
):
    if not upload_file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    request_id = requestid.get_request_id()
    uploaded_file = file_uploader.upload(f"{request_id}_{upload_file.filename}", upload_file)

    extract_types: list[ingestion_pipeline.ExtractorType] = []
    if auditor:
        extract_types.append("auditor")
    if date:
        extract_types.append("date")
    if supplier:
        extract_types.append("supplier")
    if findings:
        extract_types.append("findings")

    background_tasks.add_task(
        ingestion_pipeline.run,
        uploaded_file,
        request_id,
        extract_types,
    )
    logger.info(f"Submitted {uploaded_file} for processing")

    return {
        "request_id": request_id,
        "links": [
            {"report": f"/reports/{request_id}"},
        ],
    }
