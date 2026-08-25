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
from marga.catalog.profiler import build_catalog, load_file
from marga.federation.sql_lens import query as sql_query

app = FastAPI(title="Marga", description="No-migration data catalog and query layer")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

SAMPLE_DIR = Path(__file__).parent.parent.parent / "sample_data"


class QueryRequest(BaseModel):
    sql: str
    file_bindings: dict[str, str]


@app.get("/catalog")
def get_catalog(files: str):
    """files = comma-separated file paths, e.g. ?files=sample_data/customers.csv,sample_data/orders.csv"""
    paths = files.split(",")
    return build_catalog(paths)


@app.get("/vitals")
def get_vitals(files: str):
    paths = files.split(",")
    catalog = build_catalog(paths)
    dataframes = {p: load_file(p) for p in paths}
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
