# 🪶 marga

**A no-migration data catalog.** Point it at your CSV or JSON files — as
many as you have, not just one — and it auto-discovers schema and
relationships across all of them, tracks lineage, flags data health,
and lets you join and query everything live through SQL. Nothing is
ever copied or migrated; every query runs against your original data.

> Named after the *marga* — the base origami fold other shapes are
> built from, without ever cutting the paper. Same idea here: many
> sources, combined and queried, nothing gets cut.

## What it does

- **Discovers** — profiles schema (types, nulls, cardinality) and infers
  relationships across CSV/JSON files automatically, with confidence scores
- **Tracks lineage** — every catalog run emits an [OpenLineage](https://openlineage.io)-style
  event: what was read, when, and a content checksum
- **Flags data health (Vitals)** — Redundant, Obsolete, Trivial data
- **Queries, unified** — SQL via DuckDB, joins across files live, no
  migration
- **Web UI + CLI** — browse the catalog, see the relationship graph, run
  queries

## Sources supported

| Source | Status | How |
|---|---|---|
| CSV, JSON, Parquet, Arrow (files) | ✅ Implemented, tested | pandas/pyarrow, no credentials |
| Postgres | ✅ Implemented, **wired into catalog + live-tested** | DuckDB `postgres_scanner`, read-only attach |
| MongoDB | ✅ Implemented, **wired into catalog + live-tested** | `pymongo` |
| Elasticsearch | ✅ Implemented, **wired into catalog + live-tested** | `elasticsearch-py` (pin `<9` to match ES 8.x server) |
| S3 (object storage) | ⚠️ Adapter implemented, **not live-tested** | DuckDB `httpfs` extension |

**`marga scan` now works against live sources, not just files.** Use a
`scheme://entity` string instead of a file path.

Credentials are managed via `.env` files (never committed — see
`.gitignore`), following the pattern `MARGA_<SOURCE>_<FIELD>`:

```bash
# For running marga CLI directly on your machine (uses localhost + mapped ports):
cp .env.host.example .env.host
# no manual `source` needed — marga auto-loads .env.host on every command

marga scan postgres://public.customers postgres://public.orders
# or mix live and local sources in one scan:
marga scan sample_data/customers.csv postgres://public.orders
```

See `marga/catalog/source_router.py` for the exact field names per
source. Credentials are never logged or written to the catalog/lineage
log. Seed MongoDB and Elasticsearch with matching demo data via
`python3 docker/seed/seed_mongo.py` and `python3 docker/seed/seed_es.py`
(after `.env.host` exists — the seed scripts auto-load it the same way).

**On Docker/Kubernetes:** the code only ever reads `os.environ` — it has
no idea whether a value came from `.env.host`, a shell export, a Docker
Compose `environment:` block, or a Kubernetes `Secret`/`ConfigMap` via
`envFrom`. `.env`/`.env.host` are local-development conveniences only;
in Docker (see `docker-compose.yml`) or Kubernetes, the runtime injects
environment variables directly and `python-dotenv`'s auto-load is a
no-op (no `.env.host` file exists in those environments, and none is
needed).

`pytest tests/integration/ -v` runs the live adapter tests (auto-skipped
if a service isn't reachable, with the actual connection error shown in
the skip reason if it fails).

## Catalog persistence

Descriptions, owners, and tags for each source now persist across
scans (SQLite by default, `marga/catalog/catalog_store.db`, gitignored
— local state, not committed). The catalog data itself is still
computed fresh every scan; only human-supplied metadata is stored.
Every change is recorded with who made it and when:

```bash
marga describe sample_data/customers.csv \
  --description "Customer master list" --owner "data-team" \
  --tag pii --tag core

marga history sample_data/customers.csv
```

Or edit inline via the "edit" button next to any source in the web UI.
A completeness score (% of description/owner/tags filled in) shows
next to each source — a cheap first signal for "how well-documented is
this part of the catalog."

## Quickstart

```bash
pip install -e ".[dev]"

marga scan sample_data/customers.csv sample_data/orders.csv
marga vitals sample_data/customers.csv sample_data/orders.csv
marga serve   # web UI + API at http://localhost:8000
```

## Run with Docker

```bash
cp .env.example .env
docker compose up -d --build
# API + UI at http://localhost:8000
```

`.env` supplies credentials for the Postgres/MongoDB containers AND
tells the `marga` app container how to reach them — the app container
uses Docker's internal network (service names like `postgres`, not
`localhost`), which is different from `.env.host` used for running the
CLI on your own machine. Both are gitignored; only the `.example`
versions are committed.

The container mounts `sample_data/` read-only — drop your own CSV/JSON
files there (or edit the volume mount in `docker-compose.yml`) to test
against real data without rebuilding the image.

## Project layout

```
marga/
  sources/
    base.py                 SourceAdapter interface
    registry.py               plugin registration (@register decorator)
    files/file_source.py        CSV/JSON — implemented
  catalog/
    profiler.py              schema profiling, relationship inference
    lineage.py                 OpenLineage-style events
    vitals.py                   redundant/obsolete/trivial flags
  federation/
    sql_lens.py               live SQL over files via DuckDB
  api/main.py                 FastAPI backend
  cli.py                        command-line interface
ui/                     single-page web UI (no build step)
sample_data/            example CSVs for the quickstart
tests/unit/              tests
docs/PROJECT_BRIEF.md    scope and design notes
```

Sources are a plugin registry (`marga/sources/registry.py`) — adding
a new source type is one file and a `@register(...)` decorator, no core
changes. See `marga/sources/files/file_source.py` for the reference
implementation.

## What's not here (by design, for now)

Live database *query federation* (joining a Postgres table into the
same SQL query as a CSV file), a real graph query engine, NiFi
orchestration for SaaS sources (Salesforce/SharePoint/SAP), PII
flagging, and natural-language queries are real directions but
deliberately not part of this release. Source *adapters* for
Postgres/Mongo/ES/S3 exist (see table above) — what's not built yet is
wiring them into the catalog/vitals/query pipeline the way CSV/JSON
files already are.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Apache 2.0 — see [LICENSE](LICENSE).
