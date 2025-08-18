from fastapi import FastAPI

from cdie.ingestion import ingestion_api
from cdie.reports import reports_api

import logging

logger = logging.getLogger(__name__)


def _create_app() -> FastAPI:
    logger.debug("Creating app...")
    app = FastAPI(
        title="CDIE",
        version="0.1.0",
    )
    app.include_router(ingestion_api.router)
    app.include_router(reports_api.router)

    return app


app = _create_app()
