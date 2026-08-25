"""
Postgres adapter — implemented using DuckDB's postgres_scanner
extension. This attaches a live Postgres database to the DuckDB session
and queries it directly through DuckDB's engine, no separate driver or
ORM needed, no data copied — the same "query live, don't migrate"
principle as every other adapter here.

HONEST LIMITATION: not tested against a real Postgres instance in this
environment (no Docker daemon available in this sandbox, and DuckDB's
extension download is blocked by network egress rules here too). The
postgres_scanner approach is DuckDB's documented, standard method for
this. Test against docker-compose.yml's postgres service on your
machine — see tests/integration/test_postgres_source.py.

Security: use a READ-ONLY Postgres role for the credentials passed to
connect() wherever possible — this adapter has no way to enforce that
at the code level, so it must be enforced at the database grant level.
"""
from typing import Any

import duckdb
import pandas as pd

from marga.sources.base import SourceAdapter
from marga.sources.registry import register


@register("postgres")
class PostgresSourceAdapter(SourceAdapter):
    source_type = "postgres"

    def __init__(self):
        self._con: duckdb.DuckDBPyConnection | None = None

    def connect(self, resolved_credentials: dict[str, Any] | None) -> None:
        """
        resolved_credentials expected keys: host, port, dbname, user,
        password. Never logged. Passed into a DuckDB ATTACH statement —
        DuckDB holds the connection string in memory for this session only.
        """
        if not resolved_credentials:
            raise ValueError("PostgresSourceAdapter requires resolved_credentials")
        c = resolved_credentials
        conn_str = (
            f"host={c['host']} port={c.get('port', 5432)} "
            f"dbname={c['dbname']} user={c['user']} password={c['password']}"
        )
        self._con = duckdb.connect()
        self._con.execute("INSTALL postgres; LOAD postgres;")
        self._con.execute(f"ATTACH '{conn_str}' AS pg (TYPE POSTGRES, READ_ONLY);")

    def list_entities(self) -> list[str]:
        if not self._con:
            raise RuntimeError("Call connect() before list_entities()")
        rows = self._con.execute(
            "SELECT table_schema || '.' || table_name FROM pg.information_schema.tables "
            "WHERE table_schema NOT IN ('pg_catalog', 'information_schema')"
        ).fetchall()
        return [r[0] for r in rows]

    def read_sample(self, entity: str, row_limit: int = 1000) -> pd.DataFrame:
        """entity is a 'schema.table' string from list_entities()."""
        if not self._con:
            raise RuntimeError("Call connect() before read_sample()")
        return self._con.execute(f"SELECT * FROM pg.{entity} LIMIT {row_limit}").fetchdf()

    def requires_credentials(self) -> bool:
        return True
