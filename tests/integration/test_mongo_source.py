"""
Run against docker-compose.yml's mongodb service:
    docker compose up -d mongodb
    python3 -c "..." # seed a collection first, see below
    pytest tests/integration/test_mongo_source.py
"""
import pytest

from marga.sources.nosql.mongo_source import MongoSourceAdapter

CREDS = {"host": "localhost", "port": 27017, "user": "marga", "password": "marga", "dbname": "marga_demo"}


def _mongo_probe() -> str | None:
    try:
        adapter = MongoSourceAdapter()
        adapter.connect(CREDS)
        adapter.list_entities()
        return None
    except Exception as e:  # noqa: BLE001 — availability probe, capturing the real reason
        return f"{type(e).__name__}: {e}"


_mongo_error = _mongo_probe()
pytestmark = pytest.mark.skipif(
    _mongo_error is not None,
    reason=f"MongoDB not reachable — run docker compose up -d mongodb. Actual error: {_mongo_error}",
)


def test_connects_and_lists_collections():
    adapter = MongoSourceAdapter()
    adapter.connect(CREDS)
    # No seed data assumed — just confirm the call succeeds and returns a list
    assert isinstance(adapter.list_entities(), list)
