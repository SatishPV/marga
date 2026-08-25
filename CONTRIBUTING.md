# Contributing to marga

## Development setup

```bash
git clone <repo-url> && cd marga
pip install -e ".[dev]"
pytest tests/
```

## Adding a new source adapter

Sources are a plugin registry (`marga/sources/registry.py`) — this
requires no changes to core code.

1. Create a new file under `marga/sources/` (a new subfolder if it's
   a new category of source).
2. Subclass `SourceAdapter` (`marga/sources/base.py`) and implement
   `connect()`, `list_entities()`, `read_sample()`, `requires_credentials()`.
3. Decorate the class with `@register("your_source_name")`.
4. Importing your module registers the adapter — no edits needed to
   `profiler.py`, the API, or the CLI.
5. Add a test in `tests/unit/`.

See `marga/sources/files/file_source.py` for the reference
implementation of this pattern.

## Code style

- Type hints on public functions/methods.
- One module docstring per file explaining intent.
- `ruff` for linting, `mypy` for type checking — both run in CI.

## Pull requests

- Keep PRs scoped to one feature.
- Tests required for anything under `marga/`.
- CI must pass before merge.
