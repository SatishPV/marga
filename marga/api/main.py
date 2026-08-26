"""
Marga API: exposes the catalog, relationship graph, ROT flags, lineage,
and a live SQL query endpoint (via DuckDB, no migration) over your data.

Run: uvicorn marga.api.main:app --reload
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from marga.catalog import vitals as vitals_module
from marga.catalog.profiler import build_catalog
from marga.catalog.source_router import resolve_dataframe
from marga.catalog.storage.sqlite_store import SqliteCatalogStore
from marga.federation.sql_lens import query as sql_query

app = FastAPI(title="Marga", description="No-migration data catalog and query layer")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

SAMPLE_DIR = Path(__file__).parent.parent.parent / "sample_data"
catalog_store = SqliteCatalogStore()


class QueryRequest(BaseModel):
    sql: str
    file_bindings: dict[str, str]


class MetadataUpdateRequest(BaseModel):
    field: str  # "description", "owner", or "tags"
    value: str | list[str]
    actor: str = "web-ui-user"  # single-user mode placeholder — see storage/base.py


@app.get("/catalog")
def get_catalog(files: str):
    """files = comma-separated file paths, e.g. ?files=sample_data/customers.csv,sample_data/orders.csv"""
    paths = files.split(",")
    catalog = build_catalog(paths)
    # Attach persisted metadata + completeness to each entry — the
    # catalog DATA is still computed fresh every scan, only the
    # human-supplied METADATA is persisted (see storage/base.py).
    for entry in catalog["files"]:
        meta = catalog_store.get_metadata(entry["source"])
        entry["metadata"] = {
            "description": meta.description,
            "owner": meta.owner,
            "tags": meta.tags,
            "completeness": meta.completeness(),
        }
    return catalog


@app.get("/catalog/metadata")
def get_source_metadata(source: str):
    meta = catalog_store.get_metadata(source)
    return {
        "source": meta.source,
        "description": meta.description,
        "owner": meta.owner,
        "tags": meta.tags,
        "completeness": meta.completeness(),
        "updated_at": meta.updated_at,
        "updated_by": meta.updated_by,
    }


@app.patch("/catalog/metadata")
def set_source_metadata(source: str, req: MetadataUpdateRequest):
    catalog_store.set_field(source, req.field, req.value, actor=req.actor)
    return get_source_metadata(source)


@app.get("/catalog/metadata/history")
def get_metadata_history(source: str):
    history = catalog_store.get_audit_history(source)
    return [
        {"field": h.field_name, "old_value": h.old_value, "new_value": h.new_value, "actor": h.actor, "timestamp": h.timestamp}
        for h in history
    ]


@app.get("/vitals")
def get_vitals(files: str):
    paths = files.split(",")
    catalog = build_catalog(paths)
    dataframes = {p: resolve_dataframe(p) for p in paths}
    return {
        "trivial": {e["source"]: vitals_module.trivial_columns(e) for e in catalog["files"]},
        "obsolete": [vitals_module.obsolete_check(p) for p in paths],
        "redundant": vitals_module.redundant_columns(catalog["files"], dataframes),
    }


@app.post("/query")
def run_query(req: QueryRequest):
    result = sql_query(req.sql, req.file_bindings)
    return {"columns": list(result.columns), "rows": result.to_dict(orient="records")}


@app.get("/health")
def health():
    return {"status": "ok"}


# Serve the UI as static files at /
app.mount("/", StaticFiles(directory=str(Path(__file__).parent.parent.parent / "ui"), html=True), name="ui")
