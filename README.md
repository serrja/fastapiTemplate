# fastApiTemplate

Generic FastAPI foundation assembled from a pinned `serrja/pythonTemplate` snapshot. It owns HTTP/lifespan, optional PostgreSQL, installed-wheel Docker targets and the common Helm chart. Pokerlost contracts belong to the specialization.

## Generate and update

Install the maintenance lock with `make install`. Use an immutable reviewed template commit. `make version` reads the canonical template version from `pyproject.toml`; answers schema 1 is a separate generation contract.

```bash
uv run --locked copier copy --vcs-ref=<reviewed-commit> . /path/to/application \
  -d projectName=exampleApi -d withPersistence=false
cd /path/to/application
uv lock
make install
make check
make build
```

A fresh render resolves its first lock; existing applications commit and enforce that lock. `withDocker=false` selects the generic Docker quality/artifact recipe. `withKubernetes=false` omits deployment files. CI requires testing support. Defaults include real managed foundation tests; empty test collection is a failure.

For an existing clean application, run its supported Copier update against a reviewed commit, inspect unmerged paths, markers, `.rej`, deletions and the full diff, then run its checks. `PROJECT.md`, `SERVICE.md`, settings, historical migrations, seed tests and `deploy/values.yaml` remain application-owned. Managed tests use `tests/foundation/`; the shared chart is managed at `deploy/chart/`. A historical update test pins the actual earlier source commit.

## Ownership and composition

The [contribution guide](CONTRIBUTING.md) describes review, checks and artifact evidence.

Edit `overlay/`, `copier.yml`, `composition.toml` and maintenance tests. `template/`, `_sources/`, the mirrored tools and `composition.lock.json` are generated. The Python base owns the composer and its shared regression suite; copies are verified against their source identity.

```bash
make check
make coverage
make verify
```

For an intentional parent refresh, run the **reviewed parent's** composer; this also bootstraps newly introduced shared resources:

```bash
uv run --locked python /path/to/pythonTemplate/tools/compose_template.py \
  --repo . --refresh-base /path/to/pythonTemplate --smoke
```

Review the recorded parent HEAD, dirty status, content hashes and generated diff. Commit parent changes before refreshing consumers. No floating `main`, adjacent checkout or unpublished worktree is a runtime dependency.

## Tests and artifacts

`make check` measures canonical tooling separately from rendered runtime coverage. `make chart-check` runs accepted/rejected Helm schema and manifest contracts. CI renders DB/no-DB and Docker/Kubernetes on/off variants, runs full Docker checks, then freshly executes installed-wheel tests in containers. Database integration uses explicit disposable PostgreSQL, verifies commit/rollback and positive readiness. Ordinary HTTP tests use `with TestClient(...)`; a single-loop HTTPX test handles actual async DB integration.

Pydantic owns HTTP models and lazy application settings. Framework errors use FastAPI's standard
handler after sanitizing details, preserving required authentication, retry and method headers.
Persistence renders expose `migration_status.read_heads(config, connection)`: Alembic's public
APIs inspect empty, branched and non-hex revision sets, and a Pydantic receipt serializes the
result. The caller owns connections and migration execution. Generic HTTP applications do not
inherit a Typer runtime unless they need a real management CLI.

Docker targets are `dependencies`, `wheel-builder`, `quality`, `artifacts`, `test` and `runtime`. `make build` exports the wheel/sdist from the canonical recipe. `make verify` executes installed-wheel tests after building, without cached `RUN pytest`. The final image has one Uvicorn process, non-root UID 65532, normalized readable migrations, bounded SIGTERM handling and a real liveness check. Test source cannot shadow the installed package.

The chart is authored only in `overlay/deploy/chart`, propagated by verified composition/Copier and packaged into a `.tgz` artifact. It requires a runtime digest; tag-only references require explicit `localDevelopment=true`. Deployments have probes, resource limits, read-only filesystems, no token mount and no extra capabilities. Optional migrations are a pre-install/pre-upgrade Job using the same artifact and an existing Secret. Helm rollback changes application resources; it does not reverse a database migration.

`make deploy-local` in a Docker/Kubernetes render creates its own named Kind cluster and kubeconfig; a DB render creates a synthetic disposable PostgreSQL there. `make undeploy-local` deletes only that cluster. It does not deploy to a selected external context. CI also tests scaling and rollback on a disposable cluster.

## Cache and delivery

BuildKit performs a normal cached solve using the actual Dockerfile, context, file modes, lock, base digests and arguments. Download mounts and image layer cache are distinct. Tests always rerun. Source, README metadata, lock and base changes invalidate their dependent layers; test-only and chart-only changes can reuse the runtime. There is no custom build resolver.

CI uses repository-scoped GHA layer cache with separate variant, target, platform and PR/main scopes. Small distribution and coverage evidence is retained for 14 days. Separate `runtime-*` artifacts hold the tested Docker archive, its local image identity and checksums for one day. Preserve an approved candidate in authorized release storage before expiry. A Docker archive/local image ID is not a registry manifest digest. No registry is configured here; publication, release and external deployment require separately selected targets and authorization. Private caches must have access no wider than their source dependencies.

Generated projects may keep their published local commands in `Makefile.local`; Copier updates
continue to own the shared Makefile. Persistence-enabled `make test` combines a fresh real DB
integration run with isolated coverage before writing advisory coverage reports. Test-image assets include
owner tools and historical migrations while excluding `src/`; the suite asserts installed-wheel
origin so a checkout cannot silently shadow the artifact.

The primary check/build path uses Git, Make and Docker. `coverage` reports a fresh result without rerunning tests. Below 100% warns; assertions, types, configuration, builds and missing/corrupt/stale reports fail. Parent refresh is an explicit source-maintenance operation using the locked composer; it is not a runtime dependency.

Read [HTTP observability](docs/observability.md) for metrics, safe logging, registry ownership
and the supported worker model.

## 📄 License

Original additions use [MIT](LICENSE); inherited source and dependencies retain
their [notices](THIRD_PARTY_NOTICES.md). Generated projects choose `licensePolicy`
and their own holder/year through the common Python foundation.

For this template source, use `make version` and `make ci-local`; see [development](docs/development.md) and [version/release boundaries](docs/versioning.md).
