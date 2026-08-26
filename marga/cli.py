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
from marga.catalog.storage.sqlite_store import SqliteCatalogStore


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


def cmd_describe(args):
    store = SqliteCatalogStore()
    actor = args.actor or "cli-local-user"
    if args.description is not None:
        store.set_field(args.source, "description", args.description, actor=actor)
    if args.owner is not None:
        store.set_field(args.source, "owner", args.owner, actor=actor)
    if args.tag:
        store.set_field(args.source, "tags", args.tag, actor=actor)
    meta = store.get_metadata(args.source)
    print(json.dumps({
        "source": meta.source, "description": meta.description, "owner": meta.owner,
        "tags": meta.tags, "completeness": meta.completeness(),
        "updated_at": meta.updated_at, "updated_by": meta.updated_by,
    }, indent=2))


def cmd_history(args):
    store = SqliteCatalogStore()
    history = store.get_audit_history(args.source)
    for h in history:
        print(f"{h.timestamp[:19]} | {h.actor} changed {h.field_name}: {h.old_value!r} -> {h.new_value!r}")
    if not history:
        print(f"No metadata history for '{args.source}' yet.")


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

    p_describe = sub.add_parser("describe", help="Set description/owner/tags for a source, recorded with an audit trail")
    p_describe.add_argument("source", help="Source identifier, e.g. sample_data/customers.csv or postgres://public.customers")
    p_describe.add_argument("--description")
    p_describe.add_argument("--owner")
    p_describe.add_argument("--tag", action="append", help="Repeatable: --tag pii --tag core")
    p_describe.add_argument("--actor", help="Who's making this change (defaults to 'cli-local-user')")
    p_describe.set_defaults(func=cmd_describe)

    p_history = sub.add_parser("history", help="Show metadata change history for a source")
    p_history.add_argument("source")
    p_history.set_defaults(func=cmd_history)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    sys.exit(main())
