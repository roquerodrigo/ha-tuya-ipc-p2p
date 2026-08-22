from __future__ import annotations

import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).parent.parent
MANIFEST = ROOT / "custom_components" / "tuya_ipc_p2p" / "manifest.json"
SDK_PACKAGE = "tuya-ipc-p2p-sdk"


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_the_sdk_version_home_assistant_installs_is_the_tested_one():
    """The manifest pin and the dev-group pin must not drift apart."""
    requirement = next(
        item for item in _manifest()["requirements"] if item.startswith(SDK_PACKAGE)
    )
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert requirement in pyproject["dependency-groups"]["dev"]


def test_the_sdk_is_pinned_exactly():
    requirement = next(
        item for item in _manifest()["requirements"] if item.startswith(SDK_PACKAGE)
    )
    assert "==" in requirement


def test_the_manifest_declares_what_hacs_and_hassfest_require():
    manifest = _manifest()
    for key in (
        "domain",
        "name",
        "version",
        "documentation",
        "issue_tracker",
        "codeowners",
        "integration_type",
        "iot_class",
    ):
        assert manifest[key], key
    assert manifest["domain"] == "tuya_ipc_p2p"
    assert manifest["config_flow"] is True
    assert "camera" in manifest["dependencies"]


def test_the_hacs_minimum_matches_the_tested_home_assistant():
    hacs = json.loads((ROOT / "hacs.json").read_text(encoding="utf-8"))
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    pinned = next(
        item
        for item in pyproject["dependency-groups"]["dev"]
        if item.startswith("homeassistant==")
    )
    assert hacs["homeassistant"] == pinned.split("==", 1)[1]
