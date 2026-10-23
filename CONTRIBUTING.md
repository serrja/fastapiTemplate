# Contributing to fastapiTemplate

Read [AGENTS.md](AGENTS.md), [README.md](README.md) and `composition.toml`. The Python base owns shared Python tooling and composition; this repository owns the FastAPI overlay and its deployment recipe.

Run `make install`, `make compose`, `make check` and `make chart-check` with the pinned Helm toolchain. Render both persistence choices; run their locked checks and installed-wheel container suites. Use disposable PostgreSQL for transaction/readiness/migration checks. Test chart acceptance in a separate Kind context. Failed, skipped and unavailable checks remain explicit.

Review generated provenance and owner-file preservation after updates. Record statement and branch counts, missing paths, image identity, artifact checksums and any blocked delivery target in the PR. A build does not authorize publication, release or production deployment.
