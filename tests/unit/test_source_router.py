"""
Tests for source_router's own logic — scheme parsing, env var
credential resolution, error messages — none of which need a live
service. Live-source read tests are in tests/integration/.
"""
import pytest

from marga.catalog.source_router import _env_creds, resolve_dataframe


def test_local_file_path_bypasses_scheme_routing():
    df = resolve_dataframe("sample_data/customers.csv")
    assert list(df.columns) == ["id", "name", "city"]


def test_unknown_scheme_raises_clear_error():
    with pytest.raises(ValueError, match="Unknown source scheme"):
        resolve_dataframe("redis://something")


def test_postgres_missing_credentials_raises_clear_error(monkeypatch):
    for var in ["MARGA_POSTGRES_HOST", "MARGA_POSTGRES_DBNAME", "MARGA_POSTGRES_USER", "MARGA_POSTGRES_PASSWORD"]:
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(ValueError, match="MARGA_POSTGRES_HOST"):
        resolve_dataframe("postgres://public.customers")


def test_env_creds_resolves_required_and_optional(monkeypatch):
    monkeypatch.setenv("MARGA_TESTSVC_HOST", "localhost")
    monkeypatch.setenv("MARGA_TESTSVC_USER", "alice")
    monkeypatch.delenv("MARGA_TESTSVC_PORT", raising=False)

    creds = _env_creds("TESTSVC", required=["host", "user"], optional=["port"])
    assert creds == {"host": "localhost", "user": "alice"}


def test_env_creds_raises_on_missing_required(monkeypatch):
    monkeypatch.delenv("MARGA_TESTSVC_HOST", raising=False)
    with pytest.raises(ValueError, match="MARGA_TESTSVC_HOST"):
        _env_creds("TESTSVC", required=["host"])
