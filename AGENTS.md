# fastApiTemplate

Read [baseRules at the selected commit](https://raw.githubusercontent.com/serrja/baseRules/bafcb63ed94b9769a0ca098e5db4b33c55dbc1b9/docs/engineering.md) before the local contracts below. Pinned links are reading sources, not automatic
loaders or grants. Review source diff and change full-SHA links explicitly, then run
documentation checks. Local overrides cover only this repository's specialization.

This repository owns generic FastAPI source additions and an assembled Copier derivative of `pythonTemplate`. Owned Python follows PEP 8; keep external names and Pokerlost contracts separate. Use FastAPI, APIRouter, Depends, lifespan, and Pydantic directly. Read `composition.toml` and parent provenance before editing. Edit `overlay/` for FastAPI behavior; update `_sources/pythonTemplate` only through the explicit refresh command. `template/`, `tools/compose_template.py`, and `composition.lock.json` are generated source, not independent copies. Run real disposable Copier renders for both persistence choices and focused technical and update regressions. Preserve application-owned files on update.
