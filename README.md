# Compliance Document Intelligence Extractor (CDIE)

The application accepts a PDF file, and parses it for the below information:

- Auditor's Name
- Date of Audit
- Factory/Supplier Name
- A list of non-compliance issues or "findings"

The extracted information is stored in the `data` direction (under application root), as `jsonl`
files. Each extracted info also contains a confidence value associated with it, and some context
about where the info was extracted from.

Finally, a report is generated, that selects the top candidates (those with highest confidence)
of Auditor and Audit date, and all suppliers and findings.

## Setup

- Requires Python and [uv](https://docs.astral.sh/uv)
- After pulling the code, run:

```bash
uv sync

# To setup spaCy
uv pip install $(uvx spacy info en_core_web_sm --url)
```

## Running the application


### Server

Start the server by running

```bash
uv run server [-v[v]] [-P PORT] [-H HOST]
```

Pass the optional arguments `-P PORT` and `-H HOST` to set the port and host for the server.

These can also be set in a `.env` file kept in the project's root directory.

Pass `-v` or `-vv` for INFO and DEBUG level logging.

#### Interactive API documentation

The project uses FastAPI, which comes with Swagger UI, which provides an interactive API
documentation, accessible at `http://<HOST>:<PORT>/docs`.

All the APIs available on the application will be listed, all of which can be tried out.

### CLI

```bash
uv run cli [-h] [--extract [{auditor,date,factory,findings,all} ...]] -f FILE
```

#### `-f source-file`

The source pdf file. Must be located under `{APP_ROOT}/resources`

#### `--extract [{auditor,date,factory,findings,all} ...]` (optional)

To extract only some of the information, say "auditor" and "findings", 
pass `--extract audtior findings` etc.

#### `-v[v]` (optional)

For verbose output. `-v` set the log level to `INFO`, and `-vv` to DEBUG.
If not passed, the level will be `WARNING`.
