"""Small Prometheus metrics endpoint for the bot runtime."""

from dataclasses import dataclass
import logging
from time import monotonic

from aiohttp import web


logger = logging.getLogger(__name__)

@dataclass(slots=True)
class MetricsServer:
    """Expose process-level metrics without adding a full web application."""
    
    enabled: bool
    host: str
    port: int
    _runner: web.AppRunner | None = None
    _started_at: float = 0.0
    
    async def start(self) -> None:
        """Start the metrics HTTP endpoint when metrics are enabled."""
        
        if not self.enabled:
            logger.info("prometheus metrics endpoint disabled")
            return
        
        self._started_at = monotonic()
        app = web.Application()
        app.router.add_get("/metrics", self._handle_metrics)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        self._runner = runner
        logger.info(
            "prometheus metrics endpoint started",
            extra={"metrics_host": self.host, "metrics_port": self.port},
        )
    
    async def stop(self) -> None:
        """Stop the metrics HTTP endpoint if it was started."""
        
        if self._runner is None:
            return
        await self._runner.cleanup()
        self._runner = None
        logger.info("prometheus metrics endpoint stopped")
    
    async def _handle_metrics(self, request: web.Request) -> web.Response:
        """Return the current metrics in Prometheus text format."""
        
        del request
        return web.Response(
            body=render_metrics(uptime_seconds=self.uptime_seconds()).encode("utf-8"),
            content_type="text/plain; version=0.0.4; charset=utf-8",
        )
    
    def uptime_seconds(self) -> float:
        """Return uptime for the metrics endpoint."""
        
        if self._started_at <= 0:
            return 0.0
        return max(0.0, monotonic() - self._started_at)


def render_metrics(*, uptime_seconds: float) -> str:
    """Render the Prometheus text exposition for core application metrics."""
    
    return "\n".join([
        "# HELP yuqa_app_up Whether the Yuqa bot process is running.",
        "# TYPE yuqa_app_up gauge",
        "yuqa_app_up 1",
        "# HELP yuqa_app_uptime_seconds Bot process uptime in seconds.",
        "# TYPE yuqa_app_uptime_seconds gauge",
        f"yuqa_app_uptime_seconds {uptime_seconds:.3f}",
        "",
    ])


__all__ = ["MetricsServer", "render_metrics"]
