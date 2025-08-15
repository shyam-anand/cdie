# Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src/ src/
COPY resources/ resources/
COPY README.md .
# COPY .env .
# COPY .secrets/ .secrets/

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# Install spaCy model
RUN uv pip install $(uvx spacy info en_core_web_sm --url)



# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT []

# Default command (can be overridden in docker-compose.yml)
CMD ["uv", "run", "server", "-vv"] 