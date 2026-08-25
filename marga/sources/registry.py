"""
Source adapter registry: a plugin pattern so adding a new source type
means writing one adapter file and registering it here (or via a
setuptools entry point for external/third-party adapters) — never
editing profiler.py, the API, or the CLI.

Built-in adapters register themselves by importing this module and
calling register(). Third-party adapters (installed as separate pip
packages) can register via the "marga.sources" entry point group
declared in pyproject.toml — see docs/CONTRIBUTING.md for the walkthrough
on adding a new adapter either way.
"""
from marga.sources.base import SourceAdapter

_REGISTRY: dict[str, type[SourceAdapter]] = {}


def register(source_type: str):
    """Class decorator: @register("s3") on a SourceAdapter subclass."""
    def _wrap(adapter_cls: type[SourceAdapter]) -> type[SourceAdapter]:
        if source_type in _REGISTRY:
            raise ValueError(f"Source type '{source_type}' is already registered")
        _REGISTRY[source_type] = adapter_cls
        return adapter_cls
    return _wrap


def get_adapter(source_type: str) -> type[SourceAdapter]:
    if source_type not in _REGISTRY:
        raise KeyError(
            f"No adapter registered for '{source_type}'. "
            f"Available: {sorted(_REGISTRY.keys())}"
        )
    return _REGISTRY[source_type]


def list_registered() -> list[str]:
    return sorted(_REGISTRY.keys())


def load_entry_point_adapters() -> None:
    """Discover and register third-party adapters installed as separate
    packages, via the 'marga.sources' entry point group. Called once
    at startup (see cli.py / api/main.py) — not required for built-in
    adapters, which self-register on import."""
    from importlib.metadata import entry_points
    for ep in entry_points(group="marga.sources"):
        ep.load()  # importing the module triggers its @register(...) decorator
