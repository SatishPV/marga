"""Tests for the catalog metadata store — persistence, completeness
scoring, and the audit trail this whole feature exists for."""
import os
import tempfile

import pytest

from marga.catalog.storage.sqlite_store import SqliteCatalogStore


@pytest.fixture
def store():
    tmpdb = tempfile.mktemp(suffix=".db")
    s = SqliteCatalogStore(db_path=tmpdb)
    yield s
    os.remove(tmpdb)


def test_unknown_source_returns_empty_metadata_not_error(store):
    meta = store.get_metadata("nonexistent-source")
    assert meta.description is None
    assert meta.owner is None
    assert meta.tags == []
    assert meta.completeness() == 0.0


def test_set_field_persists_and_is_readable(store):
    store.set_field("sample_data/customers.csv", "description", "Customer list", actor="satish")
    meta = store.get_metadata("sample_data/customers.csv")
    assert meta.description == "Customer list"
    assert meta.updated_by == "satish"


def test_completeness_score_reflects_filled_fields(store):
    source = "sample_data/orders.csv"
    assert store.get_metadata(source).completeness() == 0.0

    store.set_field(source, "description", "Order records", actor="satish")
    assert store.get_metadata(source).completeness() == pytest.approx(0.33, abs=0.01)

    store.set_field(source, "owner", "sales-team", actor="satish")
    store.set_field(source, "tags", ["core"], actor="satish")
    assert store.get_metadata(source).completeness() == 1.0


def test_audit_trail_records_old_and_new_values(store):
    source = "sample_data/customers.csv"
    store.set_field(source, "description", "First version", actor="satish")
    store.set_field(source, "description", "Second version", actor="vpichipat")

    history = store.get_audit_history(source)
    assert len(history) == 2
    assert history[0].old_value is None
    assert history[0].new_value == "First version"
    assert history[0].actor == "satish"
    assert history[1].old_value == "First version"
    assert history[1].new_value == "Second version"
    assert history[1].actor == "vpichipat"


def test_set_field_rejects_blank_actor(store):
    with pytest.raises(ValueError, match="actor is required"):
        store.set_field("sample_data/customers.csv", "description", "test", actor="")


def test_set_field_rejects_unknown_field(store):
    with pytest.raises(ValueError, match="Unknown metadata field"):
        store.set_field("sample_data/customers.csv", "not_a_real_field", "test", actor="satish")


def test_tags_round_trip_as_a_list(store):
    source = "sample_data/products.csv"
    store.set_field(source, "tags", ["pii", "core", "verified"], actor="satish")
    meta = store.get_metadata(source)
    assert meta.tags == ["pii", "core", "verified"]
