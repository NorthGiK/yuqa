FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_NO_DEV=1

WORKDIR /app

RUN useradd --create-home --uid 10001 appuser

COPY pyproject.toml main.py alembic.ini ./
COPY src ./src
COPY alembic ./alembic

RUN mkdir -p /data && chown -R appuser:appuser /app /data

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
RUN /bin/uv sync --no-cache --extra production

USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
	CMD python -m src.infrastructure.sqlalchemy.healthcheck || exit 1

CMD ["uv", "run", "main.py"]
