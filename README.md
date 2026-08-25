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

## Quickstart

```bash
pip install -e ".[dev]"

marga scan sample_data/customers.csv sample_data/orders.csv
marga vitals sample_data/customers.csv sample_data/orders.csv
marga serve   # web UI + API at http://localhost:8000
```

## Run with Docker

```bash
docker compose up --build
# API + UI at http://localhost:8000
```

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

This is a focused v1: CSV/JSON files, SQL queries, local single-user use.
Live database connections, NoSQL, graph queries, object storage, and a
natural-language query layer are real directions but deliberately not
part of this release — see `docs/PROJECT_BRIEF.md` for the reasoning.
They'll come as their own tested milestones, not as unfinished code
sitting in this repo.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Apache 2.0 — see [LICENSE](LICENSE).
