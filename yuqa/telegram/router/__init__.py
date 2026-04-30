"""Stable public surface for Telegram router helpers and handler entrypoints."""

from . import router as _router


def _reexport_public_api(module: object) -> list[str]:
    """Mirror the curated router API at the package root."""

    names = getattr(module, "__all__", [])
    globals().update({name: getattr(module, name) for name in names})
    return names


__all__ = _reexport_public_api(_router)

del _reexport_public_api
del _router
