"""
Source router: the single place that turns a "source string" from the
CLI/API into an actual DataFrame, regardless of whether it's a local
file or a live source. This is what profiler.py calls instead of
load_file() directly, so the catalog pipeline works uniformly across
every registered adapter.

Source string format:
  - No "://"           -> local file path, e.g. "sample_data/orders.csv"
  - "postgres://<entity>"       -> e.g. "postgres://public.customers"
  - "mongodb://<entity>"        -> e.g. "mongodb://orders"
  - "elasticsearch://<entity>"  -> e.g. "elasticsearch://products-index"
  - "s3://<bucket>/<key>"       -> the full URI is passed straight through,
                                    since DuckDB needs the complete path

Credentials come from environment variables, following the pattern
MARGA_<SOURCE>_<FIELD>, e.g. MARGA_POSTGRES_HOST, MARGA_POSTGRES_USER.
This is intentionally simple for now (env vars only) — a proper
SecretProvider abstraction (Vault, AWS Secrets Manager, etc.) is a
reasonable future improvement once there's a real need for it, not
before. Credentials are read here and passed straight into each
adapter's connect() — never logged, never written to the catalog or
lineage log.
"""
import os

from marga.sources.databases.postgres_source import PostgresSourceAdapter
from marga.sources.files.file_source import load_file
from marga.sources.nosql.mongo_source import MongoSourceAdapter
from marga.sources.object_storage.s3_source import S3SourceAdapter
from marga.sources.search.es_source import ElasticsearchSourceAdapter

DEFAULT_ROW_LIMIT = 10_000  # bounded read for live sources — profiling, not migration


def _env_creds(prefix: str, required: list[str], optional: list[str] | None = None) -> dict:
    optional = optional or []
    creds: dict[str, str] = {}
    missing: list[str] = []
    for field in required + optional:
        env_key = f"MARGA_{prefix}_{field.upper()}"
        value = os.environ.get(env_key)
        if value is not None:
            creds[field] = value
        elif field in required:
            missing.append(env_key)
    if missing:
        raise ValueError(f"Missing required environment variable(s) for {prefix} source: {missing}")
    return creds


def _es_creds() -> dict:
    host = os.environ.get("MARGA_ELASTICSEARCH_HOST")
    if not host:
        raise ValueError("Missing required environment variable: MARGA_ELASTICSEARCH_HOST")
    creds: dict[str, str] = {"host": host}
    if os.environ.get("MARGA_ELASTICSEARCH_API_KEY"):
        creds["api_key"] = os.environ["MARGA_ELASTICSEARCH_API_KEY"]
    elif os.environ.get("MARGA_ELASTICSEARCH_USER") and os.environ.get("MARGA_ELASTICSEARCH_PASSWORD"):
        creds["user"] = os.environ["MARGA_ELASTICSEARCH_USER"]
        creds["password"] = os.environ["MARGA_ELASTICSEARCH_PASSWORD"]
    return creds


def resolve_dataframe(source: str, row_limit: int | None = None):
    """
    The one function profiler.py needs: give it any source string, get
    back a DataFrame, regardless of what kind of source it is.
    """
    if "://" not in source:
        return load_file(source)  # local file — unchanged behavior

    scheme, _, rest = source.partition("://")
    scheme = scheme.lower()
    limit = row_limit or DEFAULT_ROW_LIMIT

    if scheme == "postgres":
        postgres_adapter = PostgresSourceAdapter()
        postgres_adapter.connect(_env_creds("POSTGRES", ["host", "dbname", "user", "password"], ["port"]))
        return postgres_adapter.read_sample(rest, row_limit=limit)

    elif scheme == "mongodb":
        mongo_adapter = MongoSourceAdapter()
        mongo_adapter.connect(_env_creds("MONGODB", ["host", "user", "password", "dbname"], ["port"]))
        return mongo_adapter.read_sample(rest, row_limit=limit)

    elif scheme == "elasticsearch":
        es_adapter = ElasticsearchSourceAdapter()
        es_adapter.connect(_es_creds())
        return es_adapter.read_sample(rest, row_limit=limit)

    elif scheme == "s3":
        s3_adapter = S3SourceAdapter()
        s3_adapter.connect(_env_creds("S3", ["access_key_id", "secret_access_key"], ["region", "endpoint"]))
        return s3_adapter.read_sample(source, row_limit=limit)  # full s3:// URI needed by DuckDB

    raise ValueError(f"Unknown source scheme: '{scheme}://'. Supported: postgres, mongodb, elasticsearch, s3, or a local file path.")
