FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    YUQA_DATA_DIR=/data \
    DATABASE_URL=sqlite:////data/yuqa.db \
    YUQA_AUTO_MIGRATE=true \
    UV_NO_DEV=1

WORKDIR /app

RUN useradd --create-home --uid 10001 appuser

COPY pyproject.toml README.md main.py alembic.ini ./
COPY alembic ./alembic
COPY yuqa ./yuqa

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN /bin/uv sync --no-cache

RUN mkdir -p /data && chown -R appuser:appuser /app /data

USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -m yuqa.infrastructure.sqlalchemy.healthcheck || exit 1

CMD ["uv", "run", "yuqa.main"]
