"""
Vitals: a health check on your data — flags what's Redundant, Obsolete,
or Trivial (still internally "ROT" analysis, the standard data-governance
term, but surfaced under a name that's self-explanatory without jargon).

- Redundant: near-duplicate columns across files (same values, different name)
- Obsolete: hasn't changed (via lineage checksum) across the last N catalog runs
- Trivial: near-constant columns (one value dominates >95% of rows) or
  near-empty columns (mostly null)

Deliberately simple heuristics for v1 — each score is a signal to review,
not an automatic delete decision.
"""
from marga.catalog.lineage import history_for


def trivial_columns(catalog_entry: dict, threshold: float = 0.95) -> list[dict]:
    """Flag columns that carry almost no information."""
    flags = []
    for col in catalog_entry["columns"]:
        if col["null_pct"] > threshold * 100:
            flags.append({"column": col["name"], "reason": "mostly_null", "null_pct": col["null_pct"]})
        elif col["distinct_count"] <= 1:
            flags.append({"column": col["name"], "reason": "constant_value"})
    return flags


def obsolete_check(source_path: str, stale_after_runs: int = 5) -> dict:
    """A file that hasn't changed (same checksum) across many runs is a
    candidate for 'obsolete' — likely a static reference table, or dead data
    nobody's updating anymore. Flags it for human review either way."""
    events = history_for(source_path)
    if len(events) < stale_after_runs:
        return {"source": source_path, "obsolete_candidate": False, "runs_observed": len(events)}
    recent_checksums = {
        next(i["facets"]["checksum"] for i in e["inputs"] if i["name"] == source_path)
        for e in events[-stale_after_runs:]
    }
    return {
        "source": source_path,
        "obsolete_candidate": len(recent_checksums) == 1,
        "runs_observed": len(events),
        "note": f"unchanged across last {stale_after_runs} runs" if len(recent_checksums) == 1 else None,
    }


def redundant_columns(catalog_entries: list[dict], dataframes: dict, overlap_threshold: float = 0.9) -> list[dict]:
    """Flag column pairs (across different files) that look like duplicated
    data rather than a legitimate join key — same values, but NOT an
    obvious id/foreign-key relationship."""
    flags = []
    for i, src in enumerate(catalog_entries):
        for tgt in catalog_entries[i + 1:]:
            src_df, tgt_df = dataframes[src["source"]], dataframes[tgt["source"]]
            for c1 in src["columns"]:
                for c2 in tgt["columns"]:
                    if c1["name"].lower() == "id" or c2["name"].lower() == "id":
                        continue  # id-like columns are relationships, not redundancy
                    try:
                        v1, v2 = set(src_df[c1["name"]].dropna()), set(tgt_df[c2["name"]].dropna())
                        if not v1 or not v2:
                            continue
                        overlap = len(v1 & v2) / min(len(v1), len(v2))
                    except Exception:
                        continue
                    if overlap > overlap_threshold:
                        flags.append({
                            "columns": [f"{src['source']}.{c1['name']}", f"{tgt['source']}.{c2['name']}"],
                            "overlap": round(overlap, 2),
                        })
    return flags
