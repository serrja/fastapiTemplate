"""Check independent chart and application metadata without deploying anything."""

from __future__ import annotations

import io
import json
import tarfile
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from overlay.docker import chart_release


def fixture(root: Path, app_version: str = "0.8.2") -> Path:
    (root / "pyproject.toml").write_text(
        f'[project]\nname="demo"\nversion="{app_version}"\n'
    )
    chart = root / "deploy/chart"
    chart.mkdir(parents=True)
    (chart / "Chart.yaml").write_text(
        "apiVersion: v2\nname: demo-chart\nversion: 0.3.0-dev.0\n"
        'appVersion: "application-owned"\n'
    )
    (root / "coverage").mkdir()
    (root / "coverage/source.json").write_text(
        json.dumps({"commit": None, "dirty": True, "contentSha256": "a" * 64})
    )
    return chart


def package(root: Path, app_version: str) -> Path:
    destination = root / "dist/charts"
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / "demo-chart-0.3.0-dev.0.tgz"
    data = yaml.safe_dump(
        {
            "apiVersion": "v2",
            "name": "demo-chart",
            "version": "0.3.0-dev.0",
            "appVersion": app_version,
        }
    ).encode()
    with tarfile.open(path, "w:gz") as archive:
        member = tarfile.TarInfo("demo-chart/Chart.yaml")
        member.size = len(data)
        archive.addfile(member, io.BytesIO(data))
    return path


def test_chart_and_app_versions_are_independent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    fixture(tmp_path)
    result = CliRunner().invoke(chart_release.app, ["version"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["application"]["version"] == "0.8.2"
    assert data["chart"] == {
        "name": "demo-chart",
        "version": "0.3.0-dev.0",
        "appVersion": "0.8.2",
    }
    package(tmp_path, "0.8.2")
    assert CliRunner().invoke(chart_release.app, ["capture"]).exit_code == 0


@pytest.mark.parametrize("app_version", ["application-owned", "0.8.1"])
def test_package_rejects_stale_application_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, app_version: str
) -> None:
    monkeypatch.chdir(tmp_path)
    fixture(tmp_path)
    package(tmp_path, app_version)
    assert CliRunner().invoke(chart_release.app, ["capture"]).exit_code != 0
