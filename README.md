# Compliance Document Intelligence Extractor (CDIE)

## Setup

- Requires [uv](https://docs.astral.sh/uv)
- After pulling the code, run:

```bash
uv sync

# To setup spaCy
uv pip install $(uvx spacy info en_core_web_sm --url)
```

## Running the application

```bash
uv run cdie -f source-file [--extract [{auditor,date,suplier,findings,all} ...]] [-v[v]]
```

### `-f source-file`

The source pdf file. Must be located under `{APP_ROOT}/resources`

### `--extract 