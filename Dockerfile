FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    YUQA_DATA_DIR=/data \
    DATABASE_URL=sqlite:////data/yuqa.db \
    YUQA_AUTO_MIGRATE=true

WORKDIR /app

RUN useradd --create-home --uid 10001 appuser

COPY pyproject.toml README.md main.py alembic.ini ./
COPY alembic ./alembic
COPY yuqa ./yuqa

RUN python -m pip install --upgrade pip && python -m pip install .

RUN mkdir -p /data && chown -R appuser:appuser /app /data

USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -m yuqa.infrastructure.sqlalchemy.healthcheck || exit 1

CMD ["python", "-m", "yuqa.main"]
