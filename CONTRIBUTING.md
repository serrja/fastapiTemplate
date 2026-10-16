# Contributing to fastApiTemplate

The shared naming, review, and version rules are owned by the existing `serrja/projectTemplates` repository (`docs/naming.md`, `docs/contributing.md`, `docs/versioning.md`, and `docs/releaseGuide.md`). This repository owns only the FastAPI overlay and its derivative source.

Read [AGENTS.md](AGENTS.md), [README.md](README.md), and `composition.toml`. Edit `overlay/`, refresh a reviewed Python-base snapshot with the command in the README, and inspect `composition.lock.json` and the derived `template/` diff. Render both persistence choices into disposable directories; run their locked Ruff, strict mypy, wheel, installed-wheel startup, and bounded health checks. Record empty test collection as `notConfigured`. A real database check uses a disposable database; a local Docker failure is not a passing container check.

Use a focused `type/shortCamelCaseIntent` branch and `type(scope): intent` PR title when publication is authorized. State the owner, compatibility impact, actual checks, downstream update order, and rollback. No local edit implies permission to commit, publish, tag, or deploy.
