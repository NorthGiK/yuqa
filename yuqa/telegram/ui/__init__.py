"""Stable public surface for Telegram markup builders."""

from . import ui as _ui


def _reexport_public_api(module: object) -> list[str]:
    """Mirror the curated UI API at the package root."""

    names = list(getattr(module, "__all__", ()))
    globals().update({name: getattr(module, name) for name in names})
    return names


__all__ = _reexport_public_api(_ui)

del _reexport_public_api
del _ui
