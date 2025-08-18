import pathlib
from fastapi import UploadFile

from cdie import config


UPLOAD_DIR = config.DATA_ROOT / "upload"
if not UPLOAD_DIR.exists():
    UPLOAD_DIR.mkdir(parents=True)


def upload(filename: str, upload_file: UploadFile) -> pathlib.Path:
    filepath = UPLOAD_DIR / filename
    with open(filepath, "wb") as f:
        f.write(upload_file.file.read())
    return filepath
