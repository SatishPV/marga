"""
SQLite-backed CatalogStore — the default. A single file on disk, no
server to run, appropriate for the single-user/small-team local
deployments this project targets. See base.py for why a Postgres
implementation would share this same interface rather than being a
separate metadata model.
"""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from marga.catalog.storage.base import AuditEntry, CatalogStore, SourceMetadata

DEFAULT_DB_PATH = Path(__file__).parent.parent / "catalog_store.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS source_metadata (
    source TEXT PRIMARY KEY,
    description TEXT,
    owner TEXT,
    tags TEXT,          -- JSON-encoded list
    updated_at TEXT,
    updated_by TEXT
);

CREATE TABLE IF NOT EXISTS metadata_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    field_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    actor TEXT NOT NULL,
    timestamp TEXT NOT NULL
);
"""


class SqliteCatalogStore(CatalogStore):
    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH):
        self.db_path = str(db_path)
        with self._connect() as con:
            con.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def get_metadata(self, source: str) -> SourceMetadata:
        with self._connect() as con:
            row = con.execute(
                "SELECT description, owner, tags, updated_at, updated_by "
                "FROM source_metadata WHERE source = ?",
                (source,),
            ).fetchone()
        if row is None:
            return SourceMetadata(source=source)
        description, owner, tags_json, updated_at, updated_by = row
        return SourceMetadata(
            source=source,
            description=description,
            owner=owner,
            tags=json.loads(tags_json) if tags_json else [],
            updated_at=updated_at,
            updated_by=updated_by,
        )

    def set_field(self, source: str, field_name: str, value: str | list[str], actor: str) -> None:
        if field_name not in ("description", "owner", "tags"):
            raise ValueError(f"Unknown metadata field: '{field_name}'")
        if not actor:
            raise ValueError("actor is required — never record a metadata change anonymously")

        current = self.get_metadata(source)
        old_value = getattr(current, field_name)
        old_value_str = json.dumps(old_value) if field_name == "tags" else old_value
        new_value_str = json.dumps(value) if field_name == "tags" else value
        now = datetime.now(timezone.utc).isoformat()

        with self._connect() as con:
            # Upsert: create the row if this source has no metadata yet,
            # otherwise update just the one field being changed.
            con.execute(
                "INSERT INTO source_metadata (source, updated_at, updated_by) "
                "VALUES (?, ?, ?) "
                "ON CONFLICT(source) DO UPDATE SET updated_at = ?, updated_by = ?",
                (source, now, actor, now, actor),
            )
            con.execute(
                f"UPDATE source_metadata SET {field_name} = ? WHERE source = ?",
                (new_value_str, source),
            )
            con.execute(
                "INSERT INTO metadata_audit (source, field_name, old_value, new_value, actor, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (source, field_name, old_value_str, new_value_str, actor, now),
            )

    def get_audit_history(self, source: str) -> list[AuditEntry]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT source, field_name, old_value, new_value, actor, timestamp "
                "FROM metadata_audit WHERE source = ? ORDER BY id ASC",
                (source,),
            ).fetchall()
        return [AuditEntry(*row) for row in rows]
