# SPDX-FileCopyrightText: Copyright (c) 2026 SanHsien
# SPDX-License-Identifier: Apache-2.0
"""Tests for the fork-owned divergence and pin-bounds gates."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_tool(name: str):
    path = REPO_ROOT / "tools" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


divergence = load_tool("check_divergence")
pins = load_tool("check_pin_bounds")


def test_divergence_registry_parser_ignores_other_tables() -> None:
    text = """## 分岔清單
| 上游檔案 | 判定 |
|---|---|
| `src/owned.py` | 保留 |

## 已知問題
| `tests/not-a-registry-row.py` | 說明 |
"""
    assert divergence.registered_paths(text) == {"src/owned.py"}


def test_divergent_paths_ignore_fork_additions_and_map_readme_mirror() -> None:
    pairs = [("M", "src/owned.py"), ("A", "tools/new.py"), ("A", "README.en.md")]
    assert divergence.divergent_paths(pairs, {"src/owned.py", "README.md"}) == {
        "src/owned.py",
        "README.md",
    }


def write_dependency_fixture(root: Path, *, requirement: str, locked: str | None) -> None:
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "demo"\nversion = "1.0"\ndependencies = ["{requirement}"]\n',
        encoding="utf-8",
    )
    package = "" if locked is None else f'[[package]]\nname = "demo-dep"\nversion = "{locked}"\n'
    (root / "uv.lock").write_text(f"version = 1\n{package}", encoding="utf-8")


@pytest.mark.parametrize(
    ("requirement", "locked", "kind"),
    [
        ("demo-dep>=2,<3", "2.5", None),
        ("demo-dep>=2,<3", "3.0", "out-of-range"),
        ("demo-dep>=2", None, "missing"),
    ],
)
def test_pin_bounds(tmp_path: Path, requirement: str, locked: str | None, kind: str | None) -> None:
    write_dependency_fixture(tmp_path, requirement=requirement, locked=locked)
    requirements, versions = pins.collect(tmp_path)
    violations = pins.find_violations(requirements, versions)
    assert ([item["kind"] for item in violations] or [None]) == [kind]
