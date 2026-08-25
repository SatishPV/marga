"""
Elasticsearch adapter — profiles indices as a source (list indices,
sample documents), distinct from the future graph query lens (which
would query the RELATIONSHIP graph through ES — a different, still
roadmap feature). This adapter is about treating ES indices as just
another profileable/queryable data source, same interface as everything
else in sources/.

HONEST LIMITATION: not tested against a real Elasticsearch instance in
this environment (no Docker daemon here). The elasticsearch-py client
installs and imports fine — it's the actual connection that needs a
live cluster. Test against docker-compose.yml's elasticsearch service
on your machine — see tests/integration/test_es_source.py.
"""
from typing import Any

import pandas as pd
from elasticsearch import Elasticsearch

from marga.sources.base import SourceAdapter
from marga.sources.registry import register


@register("elasticsearch")
class ElasticsearchSourceAdapter(SourceAdapter):
    source_type = "elasticsearch"

    def __init__(self):
        self._client: Elasticsearch | None = None

    def connect(self, resolved_credentials: dict[str, Any] | None) -> None:
        """
        resolved_credentials expected keys: host (e.g. 'http://localhost:9200'),
        and optionally api_key or (user, password). Never logged.
        """
        if not resolved_credentials:
            raise ValueError("ElasticsearchSourceAdapter requires resolved_credentials")
        c = resolved_credentials
        kwargs: dict[str, Any] = {"hosts": [c["host"]], "request_timeout": 5}
        if c.get("api_key"):
            kwargs["api_key"] = c["api_key"]
        elif c.get("user") and c.get("password"):
            kwargs["basic_auth"] = (c["user"], c["password"])
        self._client = Elasticsearch(**kwargs)

    def list_entities(self) -> list[str]:
        if not self._client:
            raise RuntimeError("Call connect() before list_entities()")
        indices = self._client.indices.get_alias(index="*")
        return [name for name in indices if not name.startswith(".")]  # skip system indices

    def read_sample(self, entity: str, row_limit: int = 1000) -> pd.DataFrame:
        """entity is an index name from list_entities()."""
        if not self._client:
            raise RuntimeError("Call connect() before read_sample()")
        result = self._client.search(index=entity, size=min(row_limit, 10000))
        docs = [hit["_source"] for hit in result["hits"]["hits"]]
        return pd.json_normalize(docs)

    def requires_credentials(self) -> bool:
        return True
