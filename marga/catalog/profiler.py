"""
Schema + relationship inference over any registered source — local
files (CSV/JSON/Parquet/Arrow) or live sources (Postgres, MongoDB,
Elasticsearch, S3) via source_router.py. No data is copied — only
metadata (schema, stats) is stored in the catalog.
"""
import json

from marga.catalog.lineage import dataframe_checksum, emit_event
from marga.catalog.source_router import resolve_dataframe
from marga.sources.files.file_source import (
    load_file,  # noqa: F401 — re-exported: cli.py and api/main.py import load_file from here
)


def profile_file(source: str) -> dict:
    """Produce a catalog entry: schema + basic stats, no raw data retained.
    'source' can be a local file path or a live-source string
    (e.g. 'postgres://public.customers') — see source_router.py."""
    df = resolve_dataframe(source)
    columns = []
    for col in df.columns:
        series = df[col]
        columns.append({
            "name": col,
            "dtype": str(series.dtype),
            "null_pct": round(series.isna().mean() * 100, 2),
            "distinct_count": int(series.nunique()),
            "sample_values": series.dropna().unique()[:5].tolist(),
        })
    return {
        "source": str(source),
        "row_count": len(df),
        "columns": columns,
    }


def detect_relationships(catalog_entries: list[dict], dataframes: dict) -> list[dict]:
    """
    Heuristic join detection: for each pair of sources, look for column
    name similarity + value overlap. This is intentionally simple for
    v1 — confidence score reflects how naive it is.
    """
    relationships = []
    sources = list(catalog_entries)
    for i in range(len(sources)):
        for j in range(len(sources)):
            if i == j:
                continue
            src, tgt = sources[i], sources[j]
            src_df = dataframes[src["source"]]
            tgt_df = dataframes[tgt["source"]]
            for col in src["columns"]:
                col_name = col["name"].lower()
                # heuristic: column like "x_id" or "id" referencing another source's "id"/"x"
                for tcol in tgt["columns"]:
                    tcol_name = tcol["name"].lower()
                    name_match = (
                        col_name == tcol_name
                        or col_name.replace("_id", "") in tgt["source"].lower()
                    )
                    if not name_match:
                        continue
                    try:
                        src_vals = set(src_df[col["name"]].dropna().unique())
                        tgt_vals = set(tgt_df[tcol["name"]].dropna().unique())
                        if not src_vals or not tgt_vals:
                            continue
                        overlap = len(src_vals & tgt_vals) / len(src_vals)
                    except (KeyError, TypeError, ZeroDivisionError):
                        # KeyError: column missing after a schema mismatch;
                        # TypeError: unhashable column values (can't build a set);
                        # ZeroDivisionError: src_vals ended up empty despite the check above.
                        continue
                    if overlap > 0.5:
                        relationships.append({
                            "from": f"{src['source']}.{col['name']}",
                            "to": f"{tgt['source']}.{tcol['name']}",
                            "confidence": round(overlap, 2),
                        })
    return relationships


def build_catalog(sources: list[str]) -> dict:
    """sources: mix of local file paths and/or live-source strings
    (e.g. 'sample_data/orders.csv', 'postgres://public.customers')."""
    dataframes = {s: resolve_dataframe(s) for s in sources}
    entries = [profile_file(s) for s in sources]
    entries_by_source = {e["source"]: e for e in entries}
    relationships = detect_relationships(list(entries_by_source.values()), dataframes)

    # Record lineage: this catalog-build job read these sources and
    # produced this catalog snapshot. Checksum is computed from the
    # already-loaded data (works uniformly for files and live sources —
    # see lineage.dataframe_checksum) rather than re-reading anything.
    emit_event(
        job_name="build_catalog",
        inputs=[{"name": s, "checksum": dataframe_checksum(dataframes[s])} for s in sources],
        outputs=["catalog_snapshot"],
    )

    return {
        "files": entries,
        "relationships": relationships,
    }


if __name__ == "__main__":
    import sys
    paths = sys.argv[1:]
    if not paths:
        print("Usage: python profiler.py file1.csv file2.csv ...")
        sys.exit(1)
    catalog = build_catalog(paths)
    print(json.dumps(catalog, indent=2, default=str))
