"""
Lineage tracking: records WHERE data came from and WHEN it was profiled/queried,
using an OpenLineage-style event format (the open spec Marquez implements).
We're not running Marquez — just emitting compatible JSON events to a local
log, so this could point at a real OpenLineage backend later with no rework.

Each event answers: what job ran, what did it read, what did it produce, when.
"""
import json
import uuid
import hashlib
from datetime import datetime, timezone
from pathlib import Path

LINEAGE_LOG = Path(__file__).parent / "lineage_events.jsonl"


def _file_checksum(path: str) -> str:
    """Cheap content fingerprint — lets us detect if a source file changed
    between runs without storing the file itself."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]


def emit_event(job_name: str, inputs: list[str], outputs: list[str], event_type: str = "COMPLETE") -> dict:
    """
    inputs: source file paths this job read
    outputs: catalog entries / query results this job produced
    event_type: START | COMPLETE | FAIL (OpenLineage convention)
    """
    event = {
        "eventType": event_type,
        "eventTime": datetime.now(timezone.utc).isoformat(),
        "run": {"runId": str(uuid.uuid4())},
        "job": {"name": job_name},
        "inputs": [
            {"name": p, "namespace": "file", "facets": {"checksum": _file_checksum(p)}}
            for p in inputs
        ],
        "outputs": [{"name": o, "namespace": "catalog"} for o in outputs],
    }
    with open(LINEAGE_LOG, "a") as f:
        f.write(json.dumps(event) + "\n")
    return event


def history_for(source_path: str) -> list[dict]:
    """Every recorded event that touched this source file — the 'where did
    this come from and how' answer."""
    if not LINEAGE_LOG.exists():
        return []
    events = []
    with open(LINEAGE_LOG) as f:
        for line in f:
            event = json.loads(line)
            if any(i["name"] == source_path for i in event["inputs"]):
                events.append(event)
    return events


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "history":
        for e in history_for(sys.argv[2]):
            print(json.dumps(e, indent=2))
    else:
        print("Usage: python lineage.py history <file_path>")
