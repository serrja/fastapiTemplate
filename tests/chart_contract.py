"""Render the owned chart and check its security and artifact boundaries."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
HELM = os.environ.get("HELM", "helm")
DIGEST = "sha256:" + "a" * 64


def render(*settings: str) -> subprocess.CompletedProcess[str]:
    command = [HELM, "template", "technical", str(ROOT / "overlay/deploy/chart")]
    for setting in ("image.repository=example.invalid/technical", *settings):
        command.extend(("--set", setting))
    return subprocess.run(command, capture_output=True, text=True, timeout=30)


def documents(*settings: str) -> dict[str, Any]:
    result = render(*settings)
    assert result.returncode == 0, result.stderr
    return {item["kind"]: item for item in yaml.safe_load_all(result.stdout)}


def test_digest_security_probes_and_service() -> None:
    objects = documents(f"image.digest={DIGEST}")
    assert set(objects) == {"Deployment", "Service", "ServiceAccount"}
    pod = objects["Deployment"]["spec"]["template"]["spec"]
    container = pod["containers"][0]
    assert container["image"] == f"example.invalid/technical@{DIGEST}"
    assert pod["automountServiceAccountToken"] is False
    assert objects["ServiceAccount"]["automountServiceAccountToken"] is False
    assert pod["securityContext"]["runAsNonRoot"] is True
    assert pod["securityContext"]["runAsUser"] == 65532
    assert pod["securityContext"]["seccompProfile"]["type"] == "RuntimeDefault"
    assert container["securityContext"] == {
        "allowPrivilegeEscalation": False,
        "readOnlyRootFilesystem": True,
        "capabilities": {"drop": ["ALL"]},
    }
    assert container["readinessProbe"]["httpGet"]["path"] == "/health/ready"
    assert container["livenessProbe"]["httpGet"]["path"] == "/health/live"
    assert container["startupProbe"]["httpGet"]["port"] == "http"
    assert container["resources"]["requests"]["memory"] == "128Mi"
    assert objects["Service"]["spec"]["type"] == "ClusterIP"
    assert "env" not in container


def test_explicit_local_image_and_optional_configuration() -> None:
    objects = documents(
        "localDevelopment=true",
        "image.tag=sha-technical",
        "environment.LOG_LEVEL=DEBUG",
        "imagePullSecrets[0].name=private-pull",
        "replicaCount=3",
    )
    deployment = objects["Deployment"]["spec"]
    assert deployment["replicas"] == 3
    pod = deployment["template"]["spec"]
    assert pod["imagePullSecrets"] == [{"name": "private-pull"}]
    assert pod["containers"][0]["image"] == "example.invalid/technical:sha-technical"
    assert pod["containers"][0]["env"] == [{"name": "LOG_LEVEL", "value": "DEBUG"}]


def test_database_migration_uses_existing_secret_and_same_artifact() -> None:
    objects = documents(
        f"image.digest={DIGEST}",
        "database.enabled=true",
        "database.secretName=synthetic-reference",
        "migration.enabled=true",
    )
    job = objects["Job"]
    assert job["metadata"]["annotations"]["helm.sh/hook"] == "pre-install,pre-upgrade"
    assert job["spec"]["parallelism"] == 1
    assert job["spec"]["backoffLimit"] == 0
    pod = job["spec"]["template"]["spec"]
    assert pod["automountServiceAccountToken"] is False
    migration = pod["containers"][0]
    runtime = objects["Deployment"]["spec"]["template"]["spec"]["containers"][0]
    assert migration["image"] == runtime["image"]
    assert migration["command"] == ["python", "-m", "alembic", "upgrade", "head"]
    assert (
        migration["env"]
        == runtime["env"]
        == [
            {
                "name": "DATABASE_URL",
                "valueFrom": {
                    "secretKeyRef": {
                        "name": "synthetic-reference",
                        "key": "DATABASE_URL",
                    }
                },
            }
        ]
    )
    assert "Secret" not in objects
    assert "Role" not in objects


@pytest.mark.parametrize(
    "settings",
    [
        (),
        ("image.tag=mutable",),
        ("localDevelopment=true", "image.tag=latest"),
        ("image.digest=sha256:incomplete",),
        (f"image.digest={DIGEST}", "replicaCount=0"),
        (f"image.digest={DIGEST}", "database.enabled=true"),
        (f"image.digest={DIGEST}", "migration.enabled=true"),
        (f"image.digest={DIGEST}", "environment.DATABASE_URL=synthetic"),
        (f"image.digest={DIGEST}", "migration.activeDeadlineSeconds=0"),
        (f"image.digest={DIGEST}", "misspelledCapability=true"),
    ],
)
def test_invalid_configuration_fails(settings: tuple[str, ...]) -> None:
    result = render(*settings)
    assert result.returncode != 0
    assert result.stderr
