import json
import logging
import pathlib
from typing import TypeVar
from pydantic import BaseModel
from cdie import config

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def _get_absolute_path(path: pathlib.Path | str) -> pathlib.Path:
    if isinstance(path, str):
        path = pathlib.Path(path)
    return path if path.is_absolute() else config.DATA_ROOT / path


class JsonFileStore:
    """A simple JSON file store for storing and retrieving Pydantic models.
    The data is stored in a directory structure like this:
    <root>/<collection>/<key>.<extension>
    """

    def __init__(self, dir: pathlib.Path | str, create_dir: bool = True):
        self._dir = _get_absolute_path(dir)

        if create_dir and not self._dir.exists():
            logger.info(f"Creating directory: {self._dir}")
            self._dir.mkdir(parents=True, exist_ok=True)

    def _get_file_name(self, key: str, extension: str = "json") -> str:
        return f"{key}.{extension}" if not key.endswith(f".{extension}") else key

    def _get_dir(self, collection: str, create_dir: bool = True) -> pathlib.Path:
        dir = self._dir / collection
        if create_dir and not dir.exists():
            logger.info(f"Creating directory: {dir}")
            dir.mkdir(parents=True, exist_ok=True)
        return dir

    def read(self, collection: str, key: str, model: type[T]) -> T | None:
        """Reads a JSON file from the store and returns a Pydantic model."""
        file_path = self._get_dir(collection) / self._get_file_name(key)

        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return None

        with open(file_path, "r") as file:
            data = json.load(file)
            logger.debug(f"Read from {file_path}")
            return model.model_validate(data)

    def write(self, collection: str, key: str, data: BaseModel):
        """Writes a Pydantic model to a JSON file in the store."""
        file_path = self._get_dir(collection) / self._get_file_name(key)

        with open(file_path, "w+") as file:
            file.write(data.model_dump_json())
        logger.debug(f"Wrote to {file_path}")

    def read_list(self, collection: str, key: str, model: type[T]) -> list[T]:
        file_path = self._get_dir(collection) / self._get_file_name(key, "jsonl")
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return []

        with open(file_path, "r") as file:
            return [model.model_validate(json.loads(line.strip())) for line in file]

    def append(self, collection: str, key: str, data: BaseModel):
        """Appends a Pydantic model to a JSONL file in the store."""
        file_path = self._get_dir(collection) / self._get_file_name(key, "jsonl")

        with open(file_path, "a+") as file:
            file.write(data.model_dump_json() + "\n")
        logger.debug(f"Appended to {file_path}")
