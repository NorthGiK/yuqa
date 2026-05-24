"""Deployment file hardening checks."""

from pathlib import Path
import tomllib


ROOT = Path(__file__).resolve().parents[1]


def test_project_exposes_installed_runtime_entrypoint() -> None:
    """Containers should run the installed app, not resync the project on boot."""

    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert data["project"]["scripts"]["yuqa"] == "src.main:entrypoint"
    assert data["tool"]["uv"]["package"] is True


def test_dockerfile_uses_locked_install_and_no_env_copy() -> None:
    """The production image should be reproducible and not bake local secrets."""

    dockerfile = (ROOT / "docker" / "Dockerfile").read_text(encoding="utf-8")

    assert "COPY pyproject.toml uv.lock main.py alembic.ini ./" in dockerfile
    assert "COPY pyproject.toml main.py alembic.ini .env ./" not in dockerfile
    assert "uv sync --frozen --no-cache --extra production" in dockerfile
    assert 'CMD ["yuqa"]' in dockerfile
    assert "STOPSIGNAL SIGTERM" in dockerfile


def test_dockerignore_excludes_local_secrets_and_runtime_state() -> None:
    """Docker build context should not include local env files or databases."""

    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()

    assert ".env" in dockerignore
    assert ".env.*" in dockerignore
    assert "data/" in dockerignore
    assert "*.sqlite" in dockerignore
    assert "*.db" in dockerignore


def test_compose_hardens_bot_runtime() -> None:
    """Production compose should enable basic container hardening and log rotation."""

    compose = (ROOT / "docker" / "compose.yaml").read_text(encoding="utf-8")

    assert "read_only: true" in compose
    assert "no-new-privileges:true" in compose
    assert "cap_drop:" in compose
    assert "tmpfs:" in compose
    assert "stop_grace_period: 30s" in compose
    assert "YUQA_LOG_FORMAT: ${YUQA_LOG_FORMAT:-json}" in compose
    assert 'YUQA_METRICS_ENABLED: "true"' in compose
    assert "prom/prometheus" in compose
    assert "docker.elastic.co/elasticsearch/elasticsearch" in compose
    assert "docker.elastic.co/kibana/kibana" in compose
    assert "docker.elastic.co/beats/filebeat" in compose
    assert 'max-size: "10m"' in compose


def test_observability_configs_are_present() -> None:
    """Prometheus and Filebeat should have checked-in production configs."""

    prometheus = (ROOT / "docker" / "prometheus.yml").read_text(encoding="utf-8")
    filebeat = (ROOT / "docker" / "filebeat.yml").read_text(encoding="utf-8")

    assert "job_name: yuqa-bot" in prometheus
    assert "bot:9000" in prometheus
    assert "filebeat.autodiscover:" in filebeat
    assert "output.elasticsearch:" in filebeat
