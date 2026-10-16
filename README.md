# fastApiTemplate

A generic FastAPI Copier source assembled from a content-addressed snapshot of the existing `pythonTemplate` source (`serrja/projectTemplates`) and a small web overlay. Generated applications need no adjacent template checkout.

## 🚀 Generate

Use Copier 9.17.2 with an immutable released ref when one becomes available. A local worktree render is useful for review but records no published release identity.

```bash
destination="$(mktemp -d)"
uv run --no-project --with 'copier==9.17.2' copier copy . "$destination" \
  -d projectName=exampleApi -d withPersistence=false
cd "$destination"
uv lock
uv sync --locked
uv run --locked uvicorn exampleApi.app:createApp --factory --host 127.0.0.1 --port 8000
```

The default starts with no DSN, credentials, or product routes. Optional PostgreSQL adds engine/session and Alembic wiring without schema or automatic migration. `withTesting=false` and `withCi=false` omit those capabilities, including dependencies and workflow files.

## 🧭 Composition

`composition.toml` declares inherited paths, permitted overrides, and a smoke answer set. `_sources/pythonTemplate` is a pinned source snapshot; `template/` and `composition.lock.json` are derived and must not be edited by hand. The lock records the actual parent files, overlay, and this derivative's `copier.yml` by content SHA-256; a recorded Git HEAD alone is insufficient for dirty worktrees. The parent repository owns the composition ADR; this README contains the standalone command:

The root `tools/composeTemplate.py` is also a checked mirror of the pinned Python-base tool. An explicit parent refresh updates it after verifying that it still matches the previous snapshot.

The derivative is currently `0.1.0.dev0` with answers schema 1; these are local worktree identifiers, not a published template release. The exact source identity is in `composition.lock.json`.

```bash
uv run --no-project --with 'copier==9.17.2' python _sources/pythonTemplate/tools/composeTemplate.py --repo . --smoke
uv run --no-project --with 'copier==9.17.2' python _sources/pythonTemplate/tools/composeTemplate.py --repo . \
  --refresh-base /path/to/projectTemplates --smoke
```

The first command rebuilds from the pinned snapshot and works in a clean checkout. The second is an intentional parent update, followed by review of `composition.lock.json` and generated files. Never float the parent to `main` at generation time.

## 🛠 Development

Render both persistence choices to disposable directories. Run their locked lint/type/build commands and installed-wheel startup from another working directory. A DB readiness result needs a disposable PostgreSQL instance; no live database is used. A new scaffold has no subject test body, so test status is `notConfigured`.

The generated `PROJECT.md`, `SERVICE.md`, application code, local settings, and migrations are application-owned. In a clean generated Git checkout, run `uv run --no-project --with 'copier==9.17.2' copier update --defaults --vcs-ref=<reviewed-template-ref>`, then inspect `git status --short` for `UU` paths and review deletions. To enable persistence as part of that update, add `-d withPersistence=true`; disabling it later does not delete a project-owned revision. Controlled future updates with two real local refs verified managed changes, deletion of an unchanged file, owner preservation, optional persistence, and conflict detection. The derivative has no earlier published revision to migrate. No release, registry, or deployment target is configured here.
