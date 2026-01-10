"""
Módulo DaVinci - Integración con DaVinci Resolve.

Este módulo maneja la comunicación con DaVinci Resolve via Scripting API.
"""

# Los imports se hacen de forma lazy para evitar imports circulares
# y porque DaVinci Resolve puede no estar disponible

__all__ = [
    "ResolveAPI",
    "TimelineManager",
    "MediaPoolManager",
]


def __getattr__(name):
    """Lazy loading de clases."""
    if name == "ResolveAPI":
        from .resolve_api import ResolveAPI
        return ResolveAPI
    elif name == "TimelineManager":
        from .timeline import TimelineManager
        return TimelineManager
    elif name == "MediaPoolManager":
        from .media_pool import MediaPoolManager
        return MediaPoolManager
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
