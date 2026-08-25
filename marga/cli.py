"""
Marga CLI.

Usage:
    marga scan file1.csv file2.csv        # profile + relationships + lineage
    marga vitals file1.csv file2.csv      # data health check (redundant/obsolete/trivial)
    marga serve                           # start API + UI on :8000

For live sources (postgres://, mongodb://, elasticsearch://), credentials
are read from environment variables. If a .env.host file exists in the
current directory, it's loaded automatically — no manual `source` needed.
This has NO effect inside Docker/Kubernetes, where the runtime injects
environment variables directly (there's no .env.host file to find, and
none is needed — see docker-compose.yml).
"""
import argparse
import json
import sys

from dotenv import load_dotenv

load_dotenv(".env.host")  # silently does nothing if the file isn't present

from marga.catalog import vitals as vitals_module
from marga.catalog.profiler import build_catalog
from marga.catalog.source_router import resolve_dataframe


def cmd_scan(args):
    catalog = build_catalog(args.files)
    print(json.dumps(catalog, indent=2, default=str))


def cmd_vitals(args):
    catalog = build_catalog(args.files)
    dataframes = {p: resolve_dataframe(p) for p in args.files}
    result = {
        "trivial": {e["source"]: vitals_module.trivial_columns(e) for e in catalog["files"]},
        "obsolete": [vitals_module.obsolete_check(p) for p in args.files],
        "redundant": vitals_module.redundant_columns(catalog["files"], dataframes),
    }
    print(json.dumps(result, indent=2, default=str))


def cmd_serve(args):
    import uvicorn
    uvicorn.run("marga.api.main:app", host="0.0.0.0", port=args.port, reload=False)


def main():
    parser = argparse.ArgumentParser(prog="marga", description="No-migration data catalog & query layer")
    sub = parser.add_subparsers(dest="command", required=True)

    p_scan = sub.add_parser("scan", help="Profile files, infer relationships, log lineage")
    p_scan.add_argument("files", nargs="+")
    p_scan.set_defaults(func=cmd_scan)

    p_vitals = sub.add_parser("vitals", help="Data health check: redundant/obsolete/trivial flags")
    p_vitals.add_argument("files", nargs="+")
    p_vitals.set_defaults(func=cmd_vitals)

    p_serve = sub.add_parser("serve", help="Start the API + web UI")
    p_serve.add_argument("--port", type=int, default=8000)
    p_serve.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    sys.exit(main())
