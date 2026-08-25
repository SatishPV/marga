"""
Local file adapter — CSV, JSON, Parquet, Arrow (Feather). Implemented and
tested with real files. No credentials needed for any of these formats.
"""
from pathlib import Path
from typing import Any

import pandas as pd

from marga.sources.base import SourceAdapter
from marga.sources.registry import register

SUPPORTED_SUFFIXES = {".csv", ".json", ".parquet", ".arrow", ".feather"}


def _read(path: Path, row_limit: int | None = None) -> pd.DataFrame:
    if path.suffix == ".csv":
        return pd.read_csv(path, nrows=row_limit)
    elif path.suffix == ".json":
        df = pd.read_json(path)
        return df.head(row_limit) if row_limit else df
    elif path.suffix == ".parquet":
        df = pd.read_parquet(path)
        return df.head(row_limit) if row_limit else df
    elif path.suffix in (".arrow", ".feather"):
        df = pd.read_feather(path)
        return df.head(row_limit) if row_limit else df
    raise ValueError(f"Unsupported file type: {path.suffix}")


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
        return _read(Path(entity), row_limit)

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
    return _read(Path(path), row_limit=None)
