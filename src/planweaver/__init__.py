__version__ = "0.1.0"

from .orchestrator import Orchestrator

__all__ = ["Orchestrator", "app", "__version__"]


def __getattr__(name: str):
    if name == "app":
        from .api.main import app

        return app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
