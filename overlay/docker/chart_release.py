"""Validate Helm metadata beside the canonical Python artifact evidence."""

from __future__ import annotations

import json
import tarfile
from pathlib import Path
from typing import Annotated, Any

import typer
import yaml
from pydantic import BaseModel, ConfigDict, Field

from docker import release

app = typer.Typer(pretty_exceptions_show_locals=False)


class Chart(BaseModel):
    model_config = ConfigDict(strict=True)
    name: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    version: str = Field(
        pattern=r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
    )
    app_version: str = Field(alias="appVersion")


def chart_metadata(chart_dir: Path) -> Chart:
    return Chart.model_validate(yaml.safe_load((chart_dir / "Chart.yaml").read_text()))


def metadata(chart_dir: Path) -> dict[str, Any]:
    chart = chart_metadata(chart_dir)
    name, version, kind = release.project_metadata()
    return {
        "application": {"name": name, "version": version, "kind": kind},
        "chart": {
            "name": chart.name,
            "version": chart.version,
            "appVersion": version if kind == "package" else chart.app_version,
        },
    }


def artifact(chart_dir: Path, artifact_dir: Path) -> release.Artifact:
    expected = metadata(chart_dir)["chart"]
    path = artifact_dir / "charts" / f"{expected['name']}-{expected['version']}.tgz"
    with tarfile.open(path, "r:gz") as archive:
        member = archive.extractfile(f"{expected['name']}/Chart.yaml")
        if member is None:
            raise ValueError("Helm package is missing Chart.yaml")
        actual = Chart.model_validate(yaml.safe_load(member.read()))
    if actual.model_dump(by_alias=True) != expected:
        raise ValueError(
            "Helm chart version or application version differs from its source"
        )
    return release.Artifact(
        path=path.as_posix(), sha256=release.digest(path), version=expected["version"]
    )


@app.command("version")
def version(chart_dir: Annotated[Path, typer.Option()] = Path("deploy/chart")) -> None:
    typer.echo(json.dumps(metadata(chart_dir)))


@app.command("app-version")
def app_version(
    chart_dir: Annotated[Path, typer.Option()] = Path("deploy/chart"),
) -> None:
    typer.echo(metadata(chart_dir)["chart"]["appVersion"])


@app.command("capture")
def capture(
    chart_dir: Annotated[Path, typer.Option()] = Path("deploy/chart"),
    artifact_dir: Annotated[Path, typer.Option()] = Path("dist"),
) -> None:
    evidence = release.BuildEvidence(
        source=release.source(), artifacts=[artifact(chart_dir, artifact_dir)]
    )
    release.write_json(
        release.REPORTS / "chart-build.json", evidence.model_dump(by_alias=True)
    )


@app.command("release-check")
def check(
    chart_dir: Annotated[Path, typer.Option()] = Path("deploy/chart"),
    artifact_dir: Annotated[Path, typer.Option()] = Path("dist"),
) -> None:
    release.release_check(artifact_dir=artifact_dir)
    evidence = release.BuildEvidence.model_validate_json(
        (release.REPORTS / "chart-build.json").read_text()
    )
    current = artifact(chart_dir, artifact_dir)
    if (
        evidence.source.content_sha256 != release.source().content_sha256
        or evidence.artifacts != [current]
    ):
        raise ValueError("Helm artifact or build source is stale: run make chart")
    artifacts = [*release.checked_artifacts(), current]
    release.write_json(
        release.REPORTS / "artifacts.json",
        [item.model_dump(by_alias=True) for item in artifacts],
    )
    release.write_json(release.REPORTS / "versions.json", metadata(chart_dir))
    typer.echo(f"Helm metadata verified: {current.version}; no publication")


if __name__ == "__main__":
    app()
