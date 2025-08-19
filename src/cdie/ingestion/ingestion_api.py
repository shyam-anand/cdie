import logging

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel

from cdie.ingestion import file_uploader
from cdie.ingestion import pipeline as ingestion_pipeline
from cdie.reports import requestid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


class UploadResponse(BaseModel):
    request_id: str
    links: list[dict[str, str]]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "request_id": "1234567890",
                    "links": [
                        {"report": "/reports/1234567890"},
                    ],
                }
            ]
        }
    }


@router.post(
    "/",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=UploadResponse,
    response_model_exclude_none=True,
    description="""
    The file will be processed in the background and a report will be generated.
    The report will be available at the URL returned in the response.
    """,
    summary="Submit a file for processing",
)
async def create(
    background_tasks: BackgroundTasks,
    upload_file: UploadFile = File(description="Select a PDF file to upload"),
    auditor: bool = Query(default=True, description="Extract auditor information"),
    date: bool = Query(default=True, description="Extract date information"),
    supplier: bool = Query(default=True, description="Extract supplier information"),
    findings: bool = Query(default=True, description="Extract findings information"),
    generate_report: bool = Query(
        default=True, description="Generate a report for the extracted information"
    ),
):
    if not upload_file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    if (not upload_file.content_type == "application/pdf") or (
        not upload_file.filename.endswith(".pdf")
    ):
        raise HTTPException(status_code=400, detail="File must be a PDF")

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
        generate_report,
    )
    logger.info(f"Submitted {uploaded_file} for processing")

    return UploadResponse(
        request_id=request_id,
        links=[
            {"report": f"/reports/{request_id}"},
        ],
    )
