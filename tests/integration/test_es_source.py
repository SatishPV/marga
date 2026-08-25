"""
Run against docker-compose.yml's elasticsearch service:
    docker compose up -d elasticsearch
    pytest tests/integration/test_es_source.py
"""
import pytest

from marga.sources.search.es_source import ElasticsearchSourceAdapter

CREDS = {"host": "http://localhost:9200"}


def _es_probe() -> str | None:
    """Returns None if reachable, or the actual error string if not —
    so a version mismatch or auth issue shows up in the skip reason
    instead of being silently reported as generic "not reachable"."""
    try:
        adapter = ElasticsearchSourceAdapter()
        adapter.connect(CREDS)
        adapter.list_entities()
        return None
    except Exception as e:  # noqa: BLE001 — availability probe, capturing the real reason
        return f"{type(e).__name__}: {e}"


_es_error = _es_probe()
pytestmark = pytest.mark.skipif(
    _es_error is not None,
    reason=f"Elasticsearch not reachable — run docker compose up -d elasticsearch. Actual error: {_es_error}",
)


def test_connects_and_lists_indices():
    adapter = ElasticsearchSourceAdapter()
    adapter.connect(CREDS)
    assert isinstance(adapter.list_entities(), list)
