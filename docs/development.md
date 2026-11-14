# Developing fastapiTemplate

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

For generated offline CI, first prepare a successful online run for the same source.
The Python owner validates wheel/sdist and installed-image identities; persistence
also requires the Compose images to exist locally. Offline checks reuse those bytes,
rerun acceptance, and prohibit image pulls or dependency/build fetches.

Generated HTTP applications export wheel, sdist and chart to
`dist/<source-content-sha256>/`. Build capture, release checks and offline reuse
select that same directory, preserving previous artifacts for rollback.

## Runtime and execution settings

The owned `overlay/src/{{ packageName }}/settings.py.jinja` binds
`ServiceSettings.environment` to `<PROJECT>_RUNTIME_ENVIRONMENT` with the closed
values `main`, `dev`, `test`, and `local`. The existing telemetry input
`<PROJECT>_ENVIRONMENT` keeps `local`, `dev`, `ci`, and `remote`. Both default to
`local`; Python constructors retain `environment=...`. There is no automatic mapping
between deployment and execution identities, or any HTTP wire change.

The managed settings regressions run against real Pydantic sources in both
persistence profiles, using temporary dotenv/secret fixtures and no database
connection. Existing applications own their settings; review that owner contract
explicitly when updating the template. Keep the environment assertion tests with
the corresponding model binding.
