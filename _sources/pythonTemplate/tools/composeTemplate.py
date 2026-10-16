"""Materialize a Copier source from a pinned source snapshot and explicit overlay."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import Any

IGNORED_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
}
BASE_TEMPLATE_VERSION = "0.1.0.dev0"
BASE_ANSWERS_SCHEMA = 1


def sourceFiles(root: Path) -> dict[str, Path]:
    """List regular source files, without caches or symlinks escaping the root."""
    found: dict[str, Path] = {}
    if not root.is_dir():
        raise ValueError(f"Missing source directory: {root}")
    for path in root.rglob("*"):
        if any(part in IGNORED_PARTS for part in path.relative_to(root).parts):
            continue
        if path.is_symlink():
            raise ValueError(f"Symlink in template source: {path}")
        if path.is_file() and path.suffix != ".pyc":
            found[path.relative_to(root).as_posix()] = path
    return found


def contentIdentity(files: dict[str, Path]) -> str:
    """Hash paths and bytes so renames also change the source identity."""
    digest = hashlib.sha256()
    for name, path in sorted(files.items()):
        digest.update(name.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def copyFiles(files: dict[str, Path], destination: Path) -> None:
    for name, path in files.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def loadConfig(repo: Path) -> dict[str, Any]:
    with (repo / "composition.toml").open("rb") as file:
        data: dict[str, Any] = tomllib.load(file)
    return data


def stampBase(repo: Path) -> str:
    """Stamp the direct Python Copier source without hashing the stamp itself."""
    files = {
        f"template/{name}": path
        for name, path in sourceFiles(repo / "template").items()
        if name != ".template-source.json"
    }
    files["copier.yml"] = repo / "copier.yml"
    files["tools/composeTemplate.py"] = repo / "tools/composeTemplate.py"
    identity = contentIdentity(files)
    (repo / "template/.template-source.json").write_text(
        json.dumps(
            {
                "sourceContentSha256": identity,
                "templateVersion": BASE_TEMPLATE_VERSION,
                "answersSchema": BASE_ANSWERS_SCHEMA,
                "publication": "local worktree; release status must be checked separately",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    return identity


def refreshSnapshot(repo: Path, base: Path, snapshot: Path) -> None:
    """Refresh only the declared parent Copier tree, never its Git metadata."""
    source = base / "template"
    files = sourceFiles(source)
    parentConfig = base / "copier.yml"
    parentTool = base / "tools/composeTemplate.py"
    parentRecord = base / "composition.lock.json"
    derivedTool = repo / "tools/composeTemplate.py"
    previousTool = snapshot / "tools/composeTemplate.py"
    if derivedTool.is_file() and (
        not previousTool.is_file()
        or derivedTool.read_bytes() != previousTool.read_bytes()
    ):
        raise ValueError(
            "Derivative composition tool has local edits; preserve and review them"
        )
    if not parentConfig.is_file():
        raise ValueError(f"Missing Copier configuration: {parentConfig}")
    staging = Path(
        tempfile.mkdtemp(prefix="templateSource-", dir=os.environ.get("TMPDIR"))
    )
    try:
        copyFiles(files, staging / "template")
        shutil.copy2(parentConfig, staging / "copier.yml")
        sourceSet = {f"template/{key}": value for key, value in files.items()} | {
            "copier.yml": parentConfig
        }
        if parentTool.is_file():
            (staging / "tools").mkdir()
            shutil.copy2(parentTool, staging / "tools/composeTemplate.py")
            sourceSet["tools/composeTemplate.py"] = parentTool
        if parentRecord.is_file():
            shutil.copy2(parentRecord, staging / "composition.lock.json")
            sourceSet["composition.lock.json"] = parentRecord
        identity = contentIdentity(sourceSet)
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=base,
            capture_output=True,
            text=True,
            check=False,
        )
        dirty = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=no"],
            cwd=base,
            capture_output=True,
            text=True,
            check=False,
        )
        provenance = {
            "contentSha256": identity,
            "head": head.stdout.strip() if head.returncode == 0 else None,
            "dirtyTracked": bool(dirty.stdout.strip())
            if dirty.returncode == 0
            else None,
            "note": "Content identity is authoritative; HEAD does not identify dirty content.",
        }
        (staging / "sourceIdentity.json").write_text(
            json.dumps(provenance, indent=2) + "\n"
        )
        if snapshot.exists():
            oldFiles = sourceFiles(snapshot)
            oldIdentity = contentIdentity(
                {
                    key: value
                    for key, value in oldFiles.items()
                    if key != "sourceIdentity.json"
                }
            )
            oldRecord = json.loads((snapshot / "sourceIdentity.json").read_text())
            if oldIdentity != oldRecord["contentSha256"]:
                raise ValueError(
                    "Pinned parent snapshot has local edits; preserve and review them first"
                )
            shutil.rmtree(snapshot)
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(staging), str(snapshot))
        if derivedTool.is_file():
            shutil.copy2(snapshot / "tools/composeTemplate.py", derivedTool)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def assemble(repo: Path, config: dict[str, Any]) -> dict[str, Any]:
    templateVersion = config["templateVersion"]
    answersSchema = config["answersSchema"]
    if not isinstance(templateVersion, str) or not templateVersion:
        raise ValueError("Derivative templateVersion must be a nonempty string")
    if not isinstance(answersSchema, int) or answersSchema < 1:
        raise ValueError("Derivative answersSchema must be a positive integer")
    snapshot = repo / config["snapshot"]
    derivedTool = repo / "tools/composeTemplate.py"
    if derivedTool.is_file():
        pinnedTool = snapshot / "tools/composeTemplate.py"
        if (
            not pinnedTool.is_file()
            or derivedTool.read_bytes() != pinnedTool.read_bytes()
        ):
            raise ValueError(
                "Derivative composition tool differs from the pinned parent"
            )
    overlay = repo / config["overlay"]
    output = repo / config["output"]
    identityRecord = json.loads((snapshot / "sourceIdentity.json").read_text())
    snapshotFiles = sourceFiles(snapshot)
    snapshotIdentity = contentIdentity(
        {
            key: value
            for key, value in snapshotFiles.items()
            if key != "sourceIdentity.json"
        }
    )
    if snapshotIdentity != identityRecord["contentSha256"]:
        raise ValueError("Pinned parent source identity does not match its snapshot")
    baseFiles = sourceFiles(snapshot / "template")
    overlayFiles = sourceFiles(overlay)
    include = set(config["include"])
    missing = include - baseFiles.keys()
    if missing:
        raise ValueError(f"Missing parent source paths: {sorted(missing)}")
    overrides = set(config.get("allowOverride", []))
    conflicts = include & overlayFiles.keys()
    if conflicts != overrides:
        raise ValueError(
            f"Override contract mismatch: actual={sorted(conflicts)}, declared={sorted(overrides)}"
        )
    staging = Path(
        tempfile.mkdtemp(prefix="composedTemplate-", dir=os.environ.get("TMPDIR"))
    )
    try:
        copyFiles({key: baseFiles[key] for key in include}, staging)
        for oldName, newName in config.get("retainBase", {}).items():
            if oldName not in baseFiles:
                raise ValueError(f"Missing retained base file: {oldName}")
            target = staging / newName
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(baseFiles[oldName], target)
        copyFiles(overlayFiles, staging)
        overlayIdentity = contentIdentity(overlayFiles)
        configIdentity = hashlib.sha256(
            (repo / "composition.toml").read_bytes()
        ).hexdigest()
        copierConfigIdentity = hashlib.sha256(
            (repo / "copier.yml").read_bytes()
        ).hexdigest()
        sourceIdentity = hashlib.sha256(
            f"{snapshotIdentity}:{overlayIdentity}:{configIdentity}:{copierConfigIdentity}".encode()
        ).hexdigest()
        (staging / ".template-source.json").write_text(
            json.dumps(
                {
                    "sourceContentSha256": sourceIdentity,
                    "templateVersion": templateVersion,
                    "answersSchema": answersSchema,
                    "parentContentSha256": snapshotIdentity,
                    "overlayContentSha256": overlayIdentity,
                    "configurationSha256": configIdentity,
                    "copierConfigurationSha256": copierConfigIdentity,
                    "publication": "local composition; release status must be checked separately",
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
        newFiles = sourceFiles(staging)
        previousRecordPath = repo / "composition.lock.json"
        if output.exists() and previousRecordPath.exists():
            previousRecord = json.loads(previousRecordPath.read_text())
            unexpected = sourceFiles(output).keys() - previousRecord["files"].keys()
            if unexpected:
                raise ValueError(
                    f"Unowned files in derivative output: {sorted(unexpected)}"
                )
            for name, expected in previousRecord["files"].items():
                path = output / name
                if (
                    path.exists()
                    and hashlib.sha256(path.read_bytes()).hexdigest() != expected
                ):
                    raise ValueError(
                        f"Managed derivative source edited locally: {name}"
                    )
        elif output.exists() and any(output.iterdir()):
            raise ValueError(f"Output has no ownership record: {output}")
        owners = {name: "parent" for name in include}
        owners.update({name: "overlay" for name in overlayFiles})
        owners.update(
            {new: "retainedParent" for new in config.get("retainBase", {}).values()}
        )
        owners[".template-source.json"] = "compositor"
        record = {
            "templateVersion": templateVersion,
            "answersSchema": answersSchema,
            "parentContentSha256": snapshotIdentity,
            "overlayContentSha256": overlayIdentity,
            "sourceContentSha256": sourceIdentity,
            "configurationSha256": configIdentity,
            "copierConfigurationSha256": copierConfigIdentity,
            "files": {
                name: hashlib.sha256(path.read_bytes()).hexdigest()
                for name, path in sorted(newFiles.items())
            },
            "owners": owners,
            "schema": 1,
        }
        if output.exists():
            shutil.rmtree(output)
        shutil.move(str(staging), str(output))
        previousRecordPath.write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n"
        )
        return record
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def smokeCopier(repo: Path, answers: dict[str, Any]) -> None:
    """Use actual Copier to verify the assembled repository is renderable."""
    with tempfile.TemporaryDirectory(
        prefix="copierSmoke-", dir=os.environ.get("TMPDIR")
    ) as temporary:
        destination = Path(temporary) / "render"
        command = [sys.executable, "-m", "copier", "copy", "--defaults"]
        for name, value in answers.items():
            command.extend(
                [
                    "--data",
                    f"{name}={str(value).lower() if isinstance(value, bool) else value}",
                ]
            )
        subprocess.run([*command, str(repo), str(destination)], check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--refresh-base", type=Path)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--stamp-base", action="store_true")
    args = parser.parse_args()
    repo = args.repo.resolve()
    if args.stamp_base:
        print(f"pythonTemplate={stampBase(repo)}")
        return
    config = loadConfig(repo)
    snapshot = repo / config["snapshot"]
    if args.refresh_base is not None:
        runningTool = Path(__file__).resolve()
        runningIdentity = hashlib.sha256(runningTool.read_bytes()).digest()
        refreshSnapshot(repo, args.refresh_base.resolve(), snapshot)
        if hashlib.sha256(runningTool.read_bytes()).digest() != runningIdentity:
            command = [sys.executable, str(runningTool), "--repo", str(repo)]
            if args.smoke:
                command.append("--smoke")
            subprocess.run(command, check=True)
            return
    record = assemble(repo, config)
    print(
        f"parent={record['parentContentSha256']} overlay={record['overlayContentSha256']}"
    )
    if args.smoke:
        smokeCopier(repo, config["smokeAnswers"])


if __name__ == "__main__":
    main()
