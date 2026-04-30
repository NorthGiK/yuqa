"""Stable public surface for Telegram text renderers."""

from . import texts as _texts


def _reexport_public_api(module: object) -> list[str]:
    """Mirror the curated text API at the package root."""

    names = list(getattr(module, "__all__", ()))
    globals().update({name: getattr(module, name) for name in names})
    return names


__all__ = _reexport_public_api(_texts)

del _reexport_public_api
del _texts
