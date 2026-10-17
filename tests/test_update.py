"""Verify a real Copier update preserves project-owned FastAPI files."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COPIER = [sys.executable, "-m", "copier"]


def _run(*args: str, cwd: Path | None = None) -> str:
    completed = subprocess.run(
        list(args), cwd=cwd, capture_output=True, text=True, check=True, timeout=60
    )
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
    owner_doc.write_text(owner_doc.read_text() + "\nOwner service policy.\n")
    owner_settings.write_text(owner_settings.read_text() + "\n# owner setting\n")
    _commit(output, ("SERVICE.md", "src/sampleapi/settings.py"), "owner edits")

    source_health = source / "template/src/{{ packageName }}/api/health.py.jinja"
    source_health.write_text(source_health.read_text() + "\n# managed health marker\n")
    second = _commit(
        source,
        ("template/src/{{ packageName }}/api/health.py.jinja",),
        "update managed health",
    )
    _run(*COPIER, "update", "--quiet", "--defaults", f"--vcs-ref={second}", cwd=output)
    assert "Owner service policy." in owner_doc.read_text()
    assert "# owner setting" in owner_settings.read_text()
    assert (
        "# managed health marker"
        in (output / "src/sampleapi/api/health.py").read_text()
    )
    assert not _git(output, "ls-files", "-u")
    assert not list(output.rglob("*.rej"))
