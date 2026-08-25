# Security policy

## Reporting a vulnerability

Please do not open a public GitHub issue for security vulnerabilities.
Use your platform's private vulnerability reporting feature once this
repo is public. We'll acknowledge within a reasonable window and work
with you on a fix before public disclosure.

## Security model (v1)

marga's core design choice — never migrating or copying source data
— is itself a security property: the catalog only ever stores metadata,
so a compromise of the catalog store does not expose the underlying
data.

v1 is a local, single-user tool operating on local CSV/JSON files. It
does not currently connect to any source requiring credentials, so
there is no credential-handling surface to secure yet. As adapters
requiring authentication (databases, object storage, etc.) are added in
future milestones, a credential-handling model will be documented here
before those adapters ship — not after.

### Query execution
The SQL lens (`federation/sql_lens.py`) executes user-supplied SQL
against local files via DuckDB. This is equivalent in trust level to
running SQL in your own terminal — there is no remote/multi-user
exposure in v1.

## Out of scope (v1)

Multi-tenant access control, authentication, and remote source
credentials are not applicable to this release and will be addressed
as those features are built.
