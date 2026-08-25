"""
MongoDB adapter. Documents in the same collection can have different
shapes (unlike a CSV/SQL table with a fixed column set), so read_sample()
returns a UNION schema across the sampled documents via
pd.json_normalize — profiler.py's downstream schema inference already
handles per-column null_pct/distinct_count correctly on the result,
since a field missing from some documents just shows up with a higher
null_pct, which is the accurate signal for a document store.

HONEST LIMITATION: not tested against a real MongoDB instance in this
environment (no Docker daemon here). pymongo itself installs and
imports fine — it's the actual connection that needs a live server.
Test against docker-compose.yml's mongodb service on your machine —
see tests/integration/test_mongo_source.py.
"""
from typing import Any

import pandas as pd
from pymongo import MongoClient

from marga.sources.base import SourceAdapter
from marga.sources.registry import register


@register("mongodb")
class MongoSourceAdapter(SourceAdapter):
    source_type = "mongodb"

    def __init__(self):
        self._client: MongoClient | None = None
        self._db_name: str | None = None

    def connect(self, resolved_credentials: dict[str, Any] | None) -> None:
        """
        resolved_credentials expected keys: host, port, user, password, dbname.
        Never logged. The connection URI is built here and held only on
        the MongoClient instance for this session.
        """
        if not resolved_credentials:
            raise ValueError("MongoSourceAdapter requires resolved_credentials")
        c = resolved_credentials
        uri = (
            f"mongodb://{c['user']}:{c['password']}@{c['host']}:{c.get('port', 27017)}/"
            f"?authSource=admin"
        )
        self._client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        self._db_name = c["dbname"]

    def list_entities(self) -> list[str]:
        if not self._client or not self._db_name:
            raise RuntimeError("Call connect() before list_entities()")
        return self._client[self._db_name].list_collection_names()

    def read_sample(self, entity: str, row_limit: int = 1000) -> pd.DataFrame:
        """entity is a collection name from list_entities()."""
        if not self._client or not self._db_name:
            raise RuntimeError("Call connect() before read_sample()")
        docs = list(self._client[self._db_name][entity].find().limit(row_limit))
        for d in docs:
            d.pop("_id", None)  # ObjectId isn't JSON/DataFrame-friendly by default
        return pd.json_normalize(docs)

    def requires_credentials(self) -> bool:
        return True
