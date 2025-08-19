import logging
import pathlib
import re
from typing import Iterable

import pdfplumber
from pydantic import BaseModel
from pdfplumber.pdf import PDF
from pdfplumber.table import Table

from cdie import config

logger = logging.getLogger(__name__)


NON_LATIN_RE = re.compile(r"[^\x00-\x7f]")


class PageData(BaseModel):
    page_number: int
    text: str
    tables: list[list[list[str | None]]]
    method: str


class PdfParser:
    def extract_tables_from_page(self, tables: list[Table]) -> Iterable[list[str]]:
        for table in tables:
            table_rows = table.extract()
            row_count = 0
            for row in table_rows:
                row_count += 1
                cells = [cell for cell in row if cell and cell.strip()]
                if cells:
                    yield cells

    def extract_text_from_pdf(self, pdf: PDF, remove_non_latin: bool = True) -> Iterable[PageData]:
        try:
            for page in pdf.pages:
                logger.debug(f"On page {page.page_number}")
                # images = page.images
                # logger.info(f"Ignoring {len(images)} images")

                # if tables := page.find_tables():
                #     for row in extract_tables_from_page(tables):
                #         if row:
                #             logger.info("\t".join([f"[{cell}]" for cell in row]))

                extracted_text = page.extract_text()
                text = NON_LATIN_RE.sub("", extracted_text) if remove_non_latin else extracted_text

                yield PageData(
                    page_number=page.page_number,
                    text=text,
                    tables=page.extract_tables(),
                    method="pdfplumber",
                )

        except Exception as e:
            logger.error(f"Error extracting text from {pdf}: {e}")

    def _open_pdf_file(self, file_path: pathlib.Path) -> PDF:
        file_path = config.APP_ROOT / file_path if not file_path.is_absolute() else file_path
        if not file_path.exists():
            raise FileNotFoundError(f"File {file_path} not found")
        if not file_path.suffix == ".pdf":
            raise ValueError(f"File {file_path} is not a PDF file")

        logger.info(f"Opening {file_path}")
        return pdfplumber.open(file_path)

    def parse(
        self,
        file_path: pathlib.Path,
    ) -> Iterable[PageData]:
        pdf = self._open_pdf_file(file_path)
        logger.info(f"Extracting from {file_path} ")

        was_extracted = False
        for page_data in self.extract_text_from_pdf(pdf):
            if not page_data.text:
                continue

            logger.debug(f"Processing text: {page_data.text[:500]}")

            was_extracted = True
            yield page_data

        if not was_extracted:
            logger.warning(f"No text extracted from {file_path}")
            # TODO Use OCR to extract text
