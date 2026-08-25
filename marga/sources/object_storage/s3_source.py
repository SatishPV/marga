"""
S3-compatible object storage adapter (also works for GCS/Azure via their
S3-compatible endpoints, by pointing s3_endpoint at the right URL).

Implemented using DuckDB's httpfs extension — reads Parquet/CSV/JSON
directly from a bucket, no download/migration step. list_entities()
uses DuckDB's glob() to list matching keys without reading their content.

HONEST LIMITATION: this code has NOT been tested against a real S3
bucket in this environment (no live AWS credentials or network egress
to S3 available here). The DuckDB httpfs approach itself is
well-established and documented, but you should verify this against
your own bucket/credentials before relying on it — see
tests/integration/test_s3_source.py for the test to run once you have
real credentials.
"""
from typing import Any

import duckdb
import pandas as pd

from marga.sources.base import SourceAdapter
from marga.sources.registry import register


@register("s3")
class S3SourceAdapter(SourceAdapter):
    source_type = "s3"

    def __init__(self):
        self._con: duckdb.DuckDBPyConnection | None = None
        self._bucket_prefix: str | None = None

    def connect(self, resolved_credentials: dict[str, Any] | None) -> None:
        """
        resolved_credentials expected keys: access_key_id, secret_access_key,
        region (optional), endpoint (optional, for S3-compatible services
        like GCS/MinIO). Never logged, never persisted — held only on the
        DuckDB connection object for this session.
        """
        if not resolved_credentials:
            raise ValueError("S3SourceAdapter requires resolved_credentials")
        self._con = duckdb.connect()
        self._con.execute("INSTALL httpfs; LOAD httpfs;")
        self._con.execute(f"SET s3_access_key_id='{resolved_credentials['access_key_id']}';")
        self._con.execute(f"SET s3_secret_access_key='{resolved_credentials['secret_access_key']}';")
        if resolved_credentials.get("region"):
            self._con.execute(f"SET s3_region='{resolved_credentials['region']}';")
        if resolved_credentials.get("endpoint"):
            self._con.execute(f"SET s3_endpoint='{resolved_credentials['endpoint']}';")

    def list_entities(self, bucket_path: str = "") -> list[str]:
        """bucket_path e.g. 's3://my-bucket/data/*.parquet' — glob pattern."""
        if not self._con:
            raise RuntimeError("Call connect() before list_entities()")
        rows = self._con.execute(f"SELECT * FROM glob('{bucket_path}')").fetchall()
        return [r[0] for r in rows]

    def read_sample(self, entity: str, row_limit: int = 1000) -> pd.DataFrame:
        """entity is a full s3:// URI to a single file."""
        if not self._con:
            raise RuntimeError("Call connect() before read_sample()")
        if entity.endswith(".parquet"):
            reader = f"read_parquet('{entity}')"
        elif entity.endswith(".csv"):
            reader = f"read_csv_auto('{entity}')"
        elif entity.endswith(".json"):
            reader = f"read_json_auto('{entity}')"
        else:
            raise ValueError(f"Unsupported S3 object type: {entity}")
        return self._con.execute(f"SELECT * FROM {reader} LIMIT {row_limit}").fetchdf()

    def requires_credentials(self) -> bool:
        return True
