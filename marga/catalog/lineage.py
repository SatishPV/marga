"""
Lineage tracking: records WHERE data came from and WHEN it was profiled/queried,
using an OpenLineage-style event format (the open spec Marquez implements).
We're not running Marquez — just emitting compatible JSON events to a local
log, so this could point at a real OpenLineage backend later with no rework.

Each event answers: what job ran, what did it read, what did it produce, when.

Checksums are computed from the PROFILED DATA itself (a hash of the
DataFrame's contents), not raw file bytes — this is what lets lineage
work uniformly across local files AND live sources (Postgres, MongoDB,
Elasticsearch, S3), which have no "file bytes" to read directly. It's
also a more accurate signal for files too: it changes if and only if
the actual data changes, not incidental things like file metadata.
"""
import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

LINEAGE_LOG = Path(__file__).parent / "lineage_events.jsonl"


def dataframe_checksum(df: pd.DataFrame) -> str:
    """Content fingerprint of a DataFrame — same data in, same checksum
    out, regardless of which source it came from."""
    row_hashes = pd.util.hash_pandas_object(df, index=True).values
    return hashlib.sha256(row_hashes.tobytes()).hexdigest()[:16]


def emit_event(job_name: str, inputs: list[dict], outputs: list[str], event_type: str = "COMPLETE") -> dict:
    """
    inputs: list of {"name": source identifier, "checksum": content hash}
        — the caller computes the checksum (via dataframe_checksum) since
        only the caller has already loaded the data; this module doesn't
        re-read anything.
    outputs: catalog entries / query results this job produced
    event_type: START | COMPLETE | FAIL (OpenLineage convention)
    """
    event = {
        "eventType": event_type,
        "eventTime": datetime.now(timezone.utc).isoformat(),
        "run": {"runId": str(uuid.uuid4())},
        "job": {"name": job_name},
        "inputs": [
            {"name": i["name"], "namespace": "source", "facets": {"checksum": i["checksum"]}}
            for i in inputs
        ],
        "outputs": [{"name": o, "namespace": "catalog"} for o in outputs],
    }
    with open(LINEAGE_LOG, "a") as f:
        f.write(json.dumps(event) + "\n")
    return event


def history_for(source_name: str) -> list[dict]:
    """Every recorded event that touched this source — the 'where did
    this come from and how' answer."""
    if not LINEAGE_LOG.exists():
        return []
    events = []
    with open(LINEAGE_LOG) as f:
        for line in f:
            event = json.loads(line)
            if any(i["name"] == source_name for i in event["inputs"]):
                events.append(event)
    return events


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "history":
        for e in history_for(sys.argv[2]):
            print(json.dumps(e, indent=2))
    else:
        print("Usage: python lineage.py history <source_name>")
