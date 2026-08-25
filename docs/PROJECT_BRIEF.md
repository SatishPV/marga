# marga

*Named after the marga — the foundational origami base fold that other
shapes are built from without cutting the paper. Same principle here:
many source datasets, each queryable on its own or combined with others,
viewable through different lenses (SQL, graph, NoSQL), without migrating
(cutting) any of them.*


## Problem
Mid-size teams have data scattered across many CSV/JSON files and
databases — not one dataset, many, usually unrelated in name but related
in practice (an `orders.csv` from one system, a `customers` table in
another). They don't know what they have, how the pieces relate to each
other, or how to combine and analyze them without building a full
migration/ETL pipeline first. Enterprise catalog tools (Collibra,
Reltio, Denodo) solve this but are expensive and heavy. Nothing
lightweight lets an engineer point at several raw files/DBs at once,
immediately see how they relate, join or combine them for real analysis,
and query the result as SQL or as a graph — without copying any of it
anywhere.

## MVP scope (v1 — build this, nothing else)
1. Ingest CSV and JSON files (local, no DB connectors yet).
2. Infer schema: column names, types, null rates, cardinality.
3. Infer relationships: likely joins/foreign keys across files (name +
   value-overlap heuristics to start).
4. Catalog is computed on demand from the source files each run — no
   separate metadata database in v1 (a persistent catalog store is a
   reasonable v2 addition once real usage shows it's needed).
5. Query lens — SQL: query the original files via embedded DuckDB,
   joining across multiple files live.
6. Relationship visualization — the inferred relationship graph is shown
   in the web UI (node/edge diagram). This is a *view* of the catalog's
   relationships, not a separate queryable graph engine — a real graph
   query lens (traversal, pattern matching) is a v2+ item.
7. Lineage: every catalog build emits an OpenLineage-style event (source
   file, checksum, timestamp, run ID) to a local log — answers "where did
   this come from and did it change since last time."
8. Data health (Vitals): flags redundant, obsolete, or trivial data
   using the same profiling + lineage data already collected.
9. One demo: ingest several related CSVs → see inferred relationships
   (as a diagram) → run a SQL query that joins across them live → check
   lineage and vitals.

## Explicitly OUT of scope for v1
- OCR / unstructured documents
- Live database connectors (Postgres/Mongo direct)
- A queryable graph engine (traversal/pattern-matching) — v1 only
  *visualizes* inferred relationships, it doesn't let you query them as
  a graph
- NoSQL/document lens
- Object storage sources (S3/GCS/Azure)
- Natural-language query interface
- Persistent catalog storage (a real metadata DB, vs. computed on demand)
- Joins spanning a live DB + a file in the same query (joining multiple
  CSV/JSON files together already works today)
- Auth/access control (local, single-user only)

## Stack (v1, as shipped)
- Schema inference + relationship detection: Python (pandas, heuristics)
- Catalog: computed on demand from source files, not persisted to a DB
- SQL lens: DuckDB (embedded, queries files directly, joins across them)
- Lineage: local JSONL event log (OpenLineage-style)
- API: FastAPI · UI: single-page HTML, no build step · CLI: argparse
- Broader ambitions (live DB/NoSQL sources, a real graph query engine,
  object storage, NiFi orchestration, Rust performance layer) are
  deliberately NOT in this stack — they're future milestones, tested
  and added one at a time after v1 is proven in real use.

## Milestone 1 (this week)
Given 2 related CSVs (e.g. `customers.csv`, `orders.csv`), produce:
- A JSON catalog entry per file: columns, types, null %, cardinality
- A detected relationship: `orders.customer_id -> customers.id` with a
  confidence score
- A DuckDB query that joins them live, no migration

## Success criteria for v1
Can demo, in under 5 minutes, to someone unfamiliar with the project:
point at multiple files (not necessarily related by name) → see
relationships auto-detected across them, visualized as a diagram → run
one SQL query that joins across sources → check lineage and vitals for
the same sources.
