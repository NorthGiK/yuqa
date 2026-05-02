FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_NO_DEV=1

WORKDIR /app

RUN useradd --create-home --uid 10001 appuser

# copying application
COPY pyproject.toml main.py alembic.ini .env ./
COPY src ./src
COPY alembic ./alembic

# installing uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# install dependencies
RUN /bin/uv sync --no-cache --extra docker

RUN mkdir -p /data && chown -R appuser:appuser /app /data

USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -m src.infrastructure.sqlalchemy.healthcheck || exit 1

CMD ["uv", "run", "main.py"]
