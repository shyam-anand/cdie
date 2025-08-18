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
uv run cdie [-h] [--extract [{auditor,date,factory,findings,all} ...]] -f FILE
```

### `-f source-file`

The source pdf file. Must be located under `{APP_ROOT}/resources`

### `--extract [{auditor,date,factory,findings,all} ...]` (optional)

To extract only some of the information, say "auditor" and "findings", 
pass `--extract audtior findings` etc.

### `-v[v]` (optional)

For verbose output. `-v` set the log level to `INFO`, and `-vv` to DEBUG.
If not passed, the level will be `WARNING`.
