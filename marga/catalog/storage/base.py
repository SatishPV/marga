"""
CatalogStore: persists human-supplied catalog METADATA — descriptions,
owners, tags — and an audit trail of who changed what, when.

This is deliberately separate from the catalog DATA itself, which is
still computed fresh on every scan (see catalog/profiler.py) — a
source's schema/relationships are never stored, only what a human has
said ABOUT that source. This keeps the no-migration principle intact:
persistence here is opinion and annotation, not a copy of the data.

Default implementation: SQLite (sqlite_store.py) — zero setup,
appropriate for single-user/small-team local deployments, which is
this project's actual target user (see docs/PROJECT_BRIEF.md). A
Postgres-backed implementation is the natural addition for concurrent
multi-user use later, behind this SAME interface — not a second
metadata model to keep in sync.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class SourceMetadata:
    source: str
    description: str | None = None
    owner: str | None = None
    tags: list[str] = field(default_factory=list)
    updated_at: str | None = None
    updated_by: str | None = None

    def completeness(self) -> float:
        """Fraction of the three describable fields that are filled in —
        the completeness score, PIM-tool-inspired (see PROJECT_BRIEF.md)."""
        filled = sum([
            bool(self.description),
            bool(self.owner),
            bool(self.tags),
        ])
        return round(filled / 3, 2)


@dataclass
class AuditEntry:
    source: str
    field_name: str
    old_value: str | None
    new_value: str | None
    actor: str
    timestamp: str


class CatalogStore(ABC):
    @abstractmethod
    def get_metadata(self, source: str) -> SourceMetadata:
        """Returns metadata for a source. Never raises for an unknown
        source — returns an empty SourceMetadata instead, since "no
        metadata set yet" is a normal state, not an error."""
        raise NotImplementedError

    @abstractmethod
    def set_field(self, source: str, field_name: str, value: str | list[str], actor: str) -> None:
        """
        Sets ONE field (field_name is 'description', 'owner', or 'tags')
        and records an audit entry including the PREVIOUS value — the
        audit trail is the point, not just the current state.

        actor: who made the change. In single-user CLI/local mode, pass
        a fixed placeholder (e.g. "local-user") — this becomes
        meaningful once multi-user access exists, but costs nothing to
        record now. Never a blank string.
        """
        raise NotImplementedError

    @abstractmethod
    def get_audit_history(self, source: str) -> list[AuditEntry]:
        """All recorded changes for a source, oldest first."""
        raise NotImplementedError
