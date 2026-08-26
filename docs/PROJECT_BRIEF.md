# marga

*Named after the marga — the foundational origami base fold that other
shapes are built from without cutting the paper. Same principle here:
many source datasets, each queryable on its own or combined with others,
viewable through different lenses (SQL, graph, NoSQL), without migrating
(cutting) any of them.*


## Positioning: Registry-style MDM

Gartner defines four MDM implementation styles; **Registry** is the one
Marga actually is: data stays in its source systems, a lightweight
index/link layer tracks relationships across them, nothing is
physically consolidated. This isn't a loose analogy — it's the
established industry term for the no-migration principle (see ADR
0002 in `docs/adr/` if that file exists, or the "no-migration"
discussion in this doc's Problem section). Worth using this vocabulary
in the README/pitch going forward instead of inventing our own terms
for something the industry already names — it signals "we know the
space," not "we didn't do the research."

The other three MDM styles (Consolidation, Coexistence, and
Centralized) all involve creating a physically merged golden-record
store — explicitly NOT what Marga does, and shouldn't, per the
no-migration principle. Naming this distinction is itself useful
positioning: "Registry-style, not Consolidation-style" tells a
technical reader exactly what Marga will and won't do to their data.

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

## Post-v1 milestone plan

**Tomorrow (first half):** Catalog persistence — decide storage
architecture deliberately (default SQLite for single-user/small-team
deployments, Postgres as a connection-string swap for concurrent
multi-user use, same interface either way — not two separate
implementations). Adds descriptions, tags, ownership, and history,
none of which exist today since the catalog is computed fresh on every
scan. A simple completeness score per source (% of fields with a
description/tag/owner filled in) is a cheap, high-value addition once
this lands — same spirit as completeness/quality scoring in PIM tools
like Sales Layer, adapted to data-catalog fields instead of product
attributes.

Each metadata edit (a description or tag being set or changed) records
who made it and when — a minimal audit trail, not a full approval
workflow. Inspired by Pimcore's MDM framing ("every field change
traceable to its source and approver") and independently consistent
with Gartner's "stewardship" mandatory feature — but scoped down to
just the record itself (who/when), not a governance/approval system.
Single-user mode (today's default) can record "cli-local-user" as the
actor, same placeholder pattern already used in the security ADRs —
this becomes meaningful once multi-user access exists, but costs
nothing to log now.

**Tomorrow (second half, if time allows — otherwise slips to
Thursday):** New source adapters, in priority order: Google Sheets/
Excel (likely a bigger real-world gap for our target user than any
NoSQL source), generic SQL beyond Postgres, a data warehouse
connector (Snowflake/BigQuery). Each follows the existing
`SourceAdapter` plugin pattern — one file, `@register(...)`, a test.

**Thursday:** Duplicate/relationship classification tiers — exact,
near, and functional duplicate, using both value-overlap (already
computed) and schema similarity (column name/type/shape matching, not
yet computed) as two independent signals instead of one.

Open question surfaced by the MDM positioning above, not yet
scoped for a specific day: **survivorship rules** — once two sources
are confirmed to hold the same entity (a "golden record" question),
which value wins when they disagree? MDM tooling treats this as a
first-class governance question (a stewardship workflow, not just
detection). Marga only detects duplicates today; it has no opinion on
which source should be trusted. Worth deciding deliberately later
whether this belongs in Marga's Registry-style scope at all, or stays
explicitly out — a Registry-style implementation traditionally leaves
resolution to the human, which may be the right permanent answer here,
not just a temporary gap.

**Query panel wiring** (live sources queryable via SQL, not just
visible in the catalog): scoped for whichever day has room after
catalog persistence and duplicate tiering are both solid — don't rush
either of those to fit this in.
