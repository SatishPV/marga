"""
SourceAdapter: the interface every data source implements — local files,
object storage, databases, NoSQL, or a NiFi-fed enterprise system. This
is what makes adding a new source type "write one file and register it",
not "edit the core".

Security contract (see docs/adr/0004-security-model.md for the full
reasoning):
  - An adapter's connect() receives ALREADY-RESOLVED credentials from a
    SecretProvider (see security/secrets.py) — it never reads
    environment variables or files directly, and never logs whatever it
    receives.
  - read_sample() is used for schema profiling only. Adapters must
    respect the row limit passed in and must never be used to bulk-read
    an entire source into memory — the no-migration principle also
    means "no accidental full copy" during a routine catalog scan.
  - Adapters do not persist data anywhere. If a caching layer is ever
    added, it must be opt-in per adapter, not silent default behavior.
"""
from abc import ABC, abstractmethod
from typing import Any
import pandas as pd


class SourceAdapter(ABC):
    """Contract every source type (file, object storage, DB, NoSQL,
    NiFi-fed system) must implement."""

    #: Human-readable identifier shown in the catalog and UI, e.g. "s3", "postgres"
    source_type: str = "unknown"

    @abstractmethod
    def connect(self, resolved_credentials: dict[str, Any] | None) -> None:
        """
        Establish a connection. `resolved_credentials` is already
        resolved by a SecretProvider — this method must not read env
        vars, files, or any secret store directly, and must not log
        the credentials it receives.
        """
        raise NotImplementedError

    @abstractmethod
    def list_entities(self) -> list[str]:
        """List queryable entities (file paths, table names, bucket keys,
        collection names) without reading their contents."""
        raise NotImplementedError

    @abstractmethod
    def read_sample(self, entity: str, row_limit: int = 1000) -> pd.DataFrame:
        """
        Read AT MOST `row_limit` rows for profiling. Never reads a full
        source into memory — that would violate the no-migration
        principle in spirit even if the data isn't persisted afterward.
        """
        raise NotImplementedError

    @abstractmethod
    def requires_credentials(self) -> bool:
        """Whether this adapter needs resolved_credentials to function
        (False for local files, True for object storage/DB/NoSQL)."""
        raise NotImplementedError
