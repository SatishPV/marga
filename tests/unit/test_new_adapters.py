"""
Every adapter requiring credentials must reject a connect() call with
no credentials, loudly and immediately — not fail silently later, and
not accept partial/empty credentials as valid.
"""
import pytest

from marga.sources.databases.postgres_source import PostgresSourceAdapter
from marga.sources.nosql.mongo_source import MongoSourceAdapter
from marga.sources.object_storage.s3_source import S3SourceAdapter
from marga.sources.search.es_source import ElasticsearchSourceAdapter


@pytest.mark.parametrize("adapter_cls", [
    S3SourceAdapter,
    PostgresSourceAdapter,
    MongoSourceAdapter,
    ElasticsearchSourceAdapter,
])
def test_credentialed_adapter_rejects_none_credentials(adapter_cls):
    adapter = adapter_cls()
    with pytest.raises(ValueError):
        adapter.connect(None)


@pytest.mark.parametrize("adapter_cls", [
    S3SourceAdapter,
    PostgresSourceAdapter,
    MongoSourceAdapter,
    ElasticsearchSourceAdapter,
])
def test_credentialed_adapter_reports_requires_credentials(adapter_cls):
    assert adapter_cls().requires_credentials() is True


def test_file_adapter_does_not_require_credentials():
    from marga.sources.files.file_source import FileSourceAdapter
    assert FileSourceAdapter().requires_credentials() is False
