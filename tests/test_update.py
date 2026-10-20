"""Verify a real Copier update preserves project-owned FastAPI files."""

from __future__ import annotations

import io
import shlex
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASELINE_SOURCE = "610999b343178413ee49db30e5da2f6d1164d220"
COPIER = [sys.executable, "-m", "copier"]


def _run(*args: str, cwd: Path | None = None) -> str:
    completed = subprocess.run(
        list(args), cwd=cwd, capture_output=True, text=True, check=False, timeout=60
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    return completed.stdout.strip()


def _git(repo: Path, *args: str) -> str:
    return _run("git", *args, cwd=repo)


def _commit(repo: Path, paths: tuple[str, ...], message: str) -> str:
    _git(repo, "add", *paths)
    _git(
        repo,
        "-c",
        "user.name=Template Test",
        "-c",
        "user.email=template-test@example.invalid",
        "commit",
        "--quiet",
        "-m",
        message,
    )
    return _git(repo, "rev-parse", "HEAD")


def test_copier_update_keeps_owner_documents_and_settings(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    shutil.copy2(ROOT / "copier.yml", source / "copier.yml")
    shutil.copytree(ROOT / "template", source / "template")
    _git(source, "init", "--quiet")
    for directory in [".vscode", ".serena"]:
        marker = source / "template" / directory / "synthetic.txt"
        marker.parent.mkdir()
        marker.write_text("synthetic editor state")
        _git(source, "add", "--force", str(marker.relative_to(source)))
    first = _commit(source, ("copier.yml", "template"), "initial FastAPI source")

    output = tmp_path / "output"
    _run(
        *COPIER,
        "copy",
        "--quiet",
        "--defaults",
        f"--vcs-ref={first}",
        str(source),
        str(output),
        "-d",
        "projectName=sampleApi",
        "-d",
        "withPersistence=false",
        "-d",
        "withTesting=true",
        "-d",
        "withCi=false",
        "-d",
        "withDocker=false",
    )
    _git(output, "init", "--quiet")
    _commit(output, (".",), "initial render")
    owner_doc = output / "SERVICE.md"
    owner_settings = output / "src/sampleapi/settings.py"
    owner_test = output / "tests/test_http.py"
    owner_values = output / "deploy/values.yaml"
    owner_doc.write_text(owner_doc.read_text() + "\nOwner service policy.\n")
    owner_settings.write_text(owner_settings.read_text() + "\n# owner setting\n")
    owner_test.write_text(owner_test.read_text() + "\n# owner test scenario\n")
    owner_values.write_text(owner_values.read_text() + "\n# owner artifact digest\n")
    _commit(
        output,
        (
            "SERVICE.md",
            "src/sampleapi/settings.py",
            "tests/test_http.py",
            "deploy/values.yaml",
        ),
        "owner edits",
    )

    source_health = source / "template/src/{{ packageName }}/api/health.py.jinja"
    source_health.write_text(source_health.read_text() + "\n# managed health marker\n")
    source_chart = source / "template/deploy/chart/templates/service.yaml"
    source_chart.write_text(source_chart.read_text() + "\n# managed chart marker\n")
    second = _commit(
        source,
        (
            "template/src/{{ packageName }}/api/health.py.jinja",
            "template/deploy/chart/templates/service.yaml",
        ),
        "update managed health",
    )
    _run(*COPIER, "update", "--quiet", "--defaults", f"--vcs-ref={second}", cwd=output)
    assert "Owner service policy." in owner_doc.read_text()
    assert "# owner setting" in owner_settings.read_text()
    assert "# owner test scenario" in owner_test.read_text()
    assert "# owner artifact digest" in owner_values.read_text()
    assert (
        "# managed chart marker"
        in (output / "deploy/chart/templates/service.yaml").read_text()
    )
    assert (
        "# managed health marker"
        in (output / "src/sampleapi/api/health.py").read_text()
    )
    assert not (output / ".vscode").exists()
    assert not (output / ".serena").exists()
    assert not _git(output, "ls-files", "-u")
    assert not list(output.rglob("*.rej"))


@pytest.mark.parametrize("persistence", [False, True])
def test_update_from_committed_baseline_keeps_project_tests_and_data(
    tmp_path: Path, persistence: bool
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    archive = subprocess.check_output(
        ["git", "-C", str(ROOT), "archive", BASELINE_SOURCE, "copier.yml", "template"]
    )
    with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
        bundle.extractall(source, filter="data")
    _git(source, "init", "--quiet")
    first = _commit(source, ("copier.yml", "template"), "committed baseline")
    output = tmp_path / "application"
    _run(
        *COPIER,
        "copy",
        "--quiet",
        "--defaults",
        f"--vcs-ref={first}",
        str(source),
        str(output),
        "-d",
        "projectName=sampleApi",
        "-d",
        f"withPersistence={str(persistence).lower()}",
        "-d",
        "withCi=false",
        "-d",
        "withDocker=false",
    )
    _git(output, "init", "--quiet")
    _commit(output, (".",), "baseline render")
    owned = [
        output / name
        for name in (
            "SERVICE.md",
            "PROJECT.md",
            "src/sampleapi/settings.py",
            "tests/test_http.py",
        )
    ]
    if persistence:
        owned.append(output / "migrations/versions/owner_revision.py")
        owned[-1].write_text('"""Project-owned historical revision fixture."""\n')
    for path in owned:
        path.write_text(path.read_text() + "\n# Project-owned content\n")
    before = {path.relative_to(output): path.read_bytes() for path in owned}
    _commit(output, tuple(str(p) for p in before), "owner changes")
    shutil.rmtree(source / "template")
    shutil.copytree(ROOT / "template", source / "template")
    shutil.copy2(ROOT / "copier.yml", source / "copier.yml")
    second = _commit(source, ("copier.yml", "template"), "new managed foundation")
    _run(*COPIER, "update", "--quiet", "--defaults", f"--vcs-ref={second}", cwd=output)
    for path, content in before.items():
        assert (output / path).read_bytes() == content
    assert (output / "tests/foundation/test_http.py").is_file()
    assert (output / "Makefile").is_file()
    assert (output / "deploy/chart/Chart.yaml").is_file()
    assert (output / "deploy/values.yaml").is_file()
    assert not _git(output, "ls-files", "-u")
    assert not list(output.rglob("*.rej"))


@pytest.mark.parametrize("persistence", [False, True])
def test_generated_host_image_command_selects_application_tag(
    tmp_path: Path, persistence: bool
) -> None:
    """The documented host Make command must agree with runtime acceptance."""
    source = tmp_path / "source"
    source.mkdir()
    shutil.copy2(ROOT / "copier.yml", source / "copier.yml")
    shutil.copytree(ROOT / "template", source / "template")
    _git(source, "init", "--quiet")
    revision = _commit(source, ("copier.yml", "template"), "image command source")
    output = tmp_path / "application"
    _run(
        *COPIER,
        "copy",
        "--quiet",
        "--defaults",
        f"--vcs-ref={revision}",
        str(source),
        str(output),
        "-d",
        "projectName=sampleApi",
        "-d",
        f"withPersistence={str(persistence).lower()}",
        "-d",
        "withCi=false",
        "-d",
        "withDocker=true",
    )
    _git(output, "init", "--quiet")
    commands = _run("make", "--dry-run", "image", "CONTAINERIZED=0", cwd=output)
    builds = [
        shlex.split(line)
        for line in commands.splitlines()
        if line.startswith("docker buildx build ")
    ]
    assert len(builds) == 1
    command = builds[0]
    assert command[command.index("--tag") + 1] == "sampleapi:candidate"
    assert command[command.index("--target") + 1] == "runtime"
    assert "--load" in command


@pytest.mark.parametrize("runtime_docker", [False, True])
@pytest.mark.parametrize("persistence", [False, True])
def test_generated_quality_inputs_do_not_depend_on_runtime_delivery(
    tmp_path: Path, runtime_docker: bool, persistence: bool
) -> None:
    """Every supported runtime choice keeps its real Docker quality inputs."""
    source = tmp_path / "source"
    source.mkdir()
    shutil.copy2(ROOT / "copier.yml", source / "copier.yml")
    shutil.copytree(ROOT / "template", source / "template")
    _git(source, "init", "--quiet")
    revision = _commit(source, ("copier.yml", "template"), "quality source")
    output = tmp_path / "application"
    _run(
        *COPIER,
        "copy",
        "--quiet",
        "--defaults",
        f"--vcs-ref={revision}",
        str(source),
        str(output),
        "-d",
        "projectName=sampleApi",
        "-d",
        f"withPersistence={str(persistence).lower()}",
        "-d",
        f"withDocker={str(runtime_docker).lower()}",
        "-d",
        "withCi=false",
    )
    _git(output, "init", "--quiet")
    selected = "Dockerfile" if runtime_docker else "Dockerfile.quality"
    settings = _run(
        "make",
        "--silent",
        "CONTAINERIZED=0",
        "--eval=print-quality:;@echo $(QUALITY_DOCKERFILE) $(BUILD_DOCKERFILE)",
        "print-quality",
        cwd=output,
    )
    assert settings == f"{selected} {selected}"
    recipe = (output / selected).read_text()
    assert "AS quality" in recipe and "get.helm.sh/helm-" in recipe
    assert "AS test" in recipe and "AS artifacts" in recipe
    assert (output / "compose.test.yaml").exists() == persistence
    assert (output / "Dockerfile").exists() == runtime_docker
    acceptance = _run("make", "--dry-run", "CONTAINERIZED=1", "test-image", cwd=output)
    assert f"--file {selected} --target test" in acceptance
    offline = _run(
        "make", "--dry-run", "CONTAINERIZED=1", "OFFLINE=1", "test-image", cwd=output
    )
    assert "docker buildx" not in offline
    assert "docker compose" in offline or "docker run --pull=never" in offline

    reports = output / "coverage"
    reports.mkdir()
    (reports / "source.json").write_text('{"contentSha256":"' + "a" * 64 + '"}')
    artifact_dir = "dist/" + "a" * 64
    commands = _run(
        "make",
        "--silent",
        "CONTAINERIZED=0",
        (
            "--eval=print-artifacts:;@printf '%s\\n' '$(BUILD_COMMAND)' "
            "'$(BUILD_RECEIPT_COMMAND)' '$(RELEASE_CHECK_COMMAND)'"
        ),
        "print-artifacts",
        cwd=output,
    )
    assert commands.count(artifact_dir) == 3
    assert f"dest={artifact_dir}" in commands
    chart = _run(
        "make",
        "--dry-run",
        "CONTAINERIZED=1",
        f"ARTIFACT_DIR={artifact_dir}",
        "chart",
        cwd=output,
    )
    assert f'--destination "{artifact_dir}/charts"' in chart
    assert f'--artifact-dir "{artifact_dir}"' in chart
