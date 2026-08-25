"""
Run against docker-compose.yml's postgres service:
    docker compose up -d postgres
    pytest tests/integration/test_postgres_source.py

Skipped automatically if Postgres isn't reachable, so this never breaks
the normal `pytest tests/` run (see tests/unit/ for that).
"""
import pytest

from marga.sources.databases.postgres_source import PostgresSourceAdapter

CREDS = {"host": "localhost", "port": 5433, "dbname": "marga_demo", "user": "marga", "password": "marga"}


def _postgres_probe() -> str | None:
    try:
        adapter = PostgresSourceAdapter()
        adapter.connect(CREDS)
        adapter.list_entities()
        return None
    except Exception as e:  # noqa: BLE001 — availability probe, capturing the real reason
        return f"{type(e).__name__}: {e}"


_postgres_error = _postgres_probe()
pytestmark = pytest.mark.skipif(
    _postgres_error is not None,
    reason=f"Postgres not reachable — run docker compose up -d postgres. Actual error: {_postgres_error}",
)


def test_lists_seeded_tables():
    adapter = PostgresSourceAdapter()
    adapter.connect(CREDS)
    entities = adapter.list_entities()
    assert "public.customers" in entities
    assert "public.orders" in entities


def test_reads_same_relationship_as_csv_source():
    adapter = PostgresSourceAdapter()
    adapter.connect(CREDS)
    customers = adapter.read_sample("public.customers")
    orders = adapter.read_sample("public.orders")
    assert set(customers["id"]) == {1, 2, 3}
    assert set(orders["customer_id"]).issubset(set(customers["id"]))


def test_catalog_scans_live_postgres_via_source_router(monkeypatch):
    """
    This is the real end-to-end test for today's work: marga scan should
    now be able to profile a LIVE Postgres table the same way it profiles
    a CSV file, through the source_router — not just the adapter in
    isolation (that's what the tests above already cover).
    """
    monkeypatch.setenv("MARGA_POSTGRES_HOST", CREDS["host"])
    monkeypatch.setenv("MARGA_POSTGRES_PORT", str(CREDS["port"]))
    monkeypatch.setenv("MARGA_POSTGRES_DBNAME", CREDS["dbname"])
    monkeypatch.setenv("MARGA_POSTGRES_USER", CREDS["user"])
    monkeypatch.setenv("MARGA_POSTGRES_PASSWORD", CREDS["password"])

    from marga.catalog.profiler import build_catalog
    catalog = build_catalog(["postgres://public.customers", "postgres://public.orders"])

    assert len(catalog["files"]) == 2
    assert any(
        "customer_id" in r["from"] and "id" in r["to"]
        for r in catalog["relationships"]
    ), f"Expected a customer_id -> id relationship, got {catalog['relationships']}"
