"""
Local file adapter (CSV, JSON) — implemented, no credentials needed.
This is the one working SourceAdapter today; every other adapter in
sources/ is a roadmap stub implementing the same interface.
"""
from pathlib import Path
from typing import Any
import pandas as pd

from marga.sources.base import SourceAdapter
from marga.sources.registry import register


@register("file")
class FileSourceAdapter(SourceAdapter):
    source_type = "file"

    def __init__(self):
        self._entities: list[str] = []

    def connect(self, resolved_credentials: dict[str, Any] | None = None) -> None:
        # Local files need no credentials — nothing to do.
        pass

    def register_path(self, path: str) -> None:
        """Local-file-specific: add a path to this session's known entities."""
        self._entities.append(path)

    def list_entities(self) -> list[str]:
        return list(self._entities)

    def read_sample(self, entity: str, row_limit: int = 1000) -> pd.DataFrame:
        path = Path(entity)
        if path.suffix == ".csv":
            return pd.read_csv(path, nrows=row_limit)
        elif path.suffix == ".json":
            return pd.read_json(path).head(row_limit)
        raise ValueError(f"Unsupported file type: {path.suffix}")

    def requires_credentials(self) -> bool:
        return False


def load_file(path: str) -> pd.DataFrame:
    """
    Simple stateless helper used by catalog/profiler.py, which reads
    whole files for full profiling (not just a sample). Kept separate
    from the FileSourceAdapter class above, which is the pluggable,
    session-based interface other code (API, CLI) should use going
    forward as more source types are added.
    """
    path_obj = Path(path)
    if path_obj.suffix == ".csv":
        return pd.read_csv(path_obj)
    elif path_obj.suffix == ".json":
        return pd.read_json(path_obj)
    raise ValueError(f"Unsupported file type: {path_obj.suffix}")
