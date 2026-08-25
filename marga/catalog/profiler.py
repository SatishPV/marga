"""
Milestone 1: Schema + relationship inference over CSV/JSON files.
No data is copied — only metadata (schema, stats) is stored in the catalog.
"""
import json
import pandas as pd
from pathlib import Path
from marga.catalog.lineage import emit_event
from marga.sources.files.file_source import load_file  # re-exported for backward compatibility


def profile_file(path: str) -> dict:
    """Produce a catalog entry: schema + basic stats, no raw data retained."""
    df = load_file(path)
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
        "source": str(path),
        "row_count": len(df),
        "columns": columns,
    }


def detect_relationships(catalog_entries: list[dict], dataframes: dict) -> list[dict]:
    """
    Heuristic join detection: for each pair of files, look for column name
    similarity + value overlap. This is intentionally simple for v1 —
    confidence score reflects how naive it is.
    """
    relationships = []
    files = list(catalog_entries)
    for i in range(len(files)):
        for j in range(len(files)):
            if i == j:
                continue
            src, tgt = files[i], files[j]
            src_df = dataframes[src["source"]]
            tgt_df = dataframes[tgt["source"]]
            for col in src["columns"]:
                col_name = col["name"].lower()
                # heuristic: column like "x_id" or "id" referencing another file's "id"/"x"
                for tcol in tgt["columns"]:
                    tcol_name = tcol["name"].lower()
                    name_match = (
                        col_name == tcol_name
                        or col_name.replace("_id", "") in tgt["source"].lower()
                        or (tcol_name == "id" and col_name.endswith("_id"))
                    )
                    if not name_match:
                        continue
                    try:
                        src_vals = set(src_df[col["name"]].dropna().unique())
                        tgt_vals = set(tgt_df[tcol["name"]].dropna().unique())
                        if not src_vals or not tgt_vals:
                            continue
                        overlap = len(src_vals & tgt_vals) / len(src_vals)
                    except Exception:
                        continue
                    if overlap > 0.5:
                        relationships.append({
                            "from": f"{src['source']}.{col['name']}",
                            "to": f"{tgt['source']}.{tcol['name']}",
                            "confidence": round(overlap, 2),
                        })
    return relationships


def build_catalog(file_paths: list[str]) -> dict:
    dataframes = {p: load_file(p) for p in file_paths}
    entries = [profile_file(p) for p in file_paths]
    entries_by_source = {e["source"]: e for e in entries}
    relationships = detect_relationships(list(entries_by_source.values()), dataframes)

    # Record lineage: this catalog-build job read these source files and
    # produced this catalog snapshot — the "where did it come from, how"
    # answer, queryable later per file.
    emit_event(
        job_name="build_catalog",
        inputs=file_paths,
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
