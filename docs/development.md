# Developing fastApiTemplate

The native source workflow is `make install`, `make ci-local`. Its ordered targets
run quality/source tests once, report coverage, build a deterministic source bundle,
verify its bytes and validate release metadata. `coverage/ci-local.json` records
source commit, dirty/content identity, commands, tools and artifact checksums.
Coverage below 100% warns; failed, missing or stale checks never count as PASS.

`OFFLINE=1` requires the exact prepared quality image and all test inputs. The
[canonical tooling guide](https://github.com/serrja/pythonTemplate/blob/main/docs/engineering.md)
owns the Make/receipt implementation. See [versions](versioning.md) and the
[shared development policy](https://github.com/serrja/baseRules/blob/main/docs/development.md).

Generated persistence-enabled projects run source tests in a unique Compose project
with a synthetic PostgreSQL database. Cleanup removes only that run's containers and
volumes. `make verify` uses a separate installed-package contour. These local checks
need Docker Compose and the pinned database image; no existing database is selected.
