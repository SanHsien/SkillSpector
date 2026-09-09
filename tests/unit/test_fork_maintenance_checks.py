# SPDX-FileCopyrightText: Copyright (c) 2026 SanHsien
# SPDX-License-Identifier: Apache-2.0
"""Tests for the fork-owned divergence and pin-bounds gates."""

from __future__ import annotations

import importlib.util
import json
import subprocess
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
freshness = load_tool("check_dependency_freshness")


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


def test_collect_disables_rename_detection(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    base = "a" * 40
    baseline = tmp_path / "upstream_baseline.json"
    baseline.write_text(f'{{"reviewed_through": "{base}"}}', encoding="utf-8")
    calls: list[tuple[str, ...]] = []

    def fake_git(_repo: Path, *args: str) -> str:
        calls.append(args)
        if args[0] == "ls-tree":
            return "src/old_name.py\n"
        if args[0] == "diff":
            return "D\tsrc/old_name.py\nA\tsrc/new_name.py\n"
        return ""

    monkeypatch.setattr(divergence, "git", fake_git)

    assert divergence.collect(tmp_path, baseline) == (base, {"src/old_name.py"})
    assert ("diff", "--no-renames", "--name-status", base, "--") in calls


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


def test_subdirectory_actions_are_tracked_and_resolved_to_their_repository() -> None:
    """`github/codeql-action/init` is an action; its releases live on the repo."""
    text = (
        "      - uses: github/codeql-action/init@a35ac6e6798d72df5475948b28efb89edc2e19ca"
        " # v4.37.9\n"
    )

    packages = freshness.parse_workflow_actions(text, "codeql.yml")

    assert packages[0]["name"] == "github/codeql-action/init"
    assert packages[0]["minimum"] == "4.37.9"
    assert freshness.action_repository(packages[0]["name"]) == "github/codeql-action"
    assert freshness.action_repository("actions/checkout") == "actions/checkout"


def test_codeql_pins_reach_the_real_report() -> None:
    """Regression guard: the owner/repo-only pattern skipped every CodeQL pin."""
    names = {action["name"] for action in freshness.load_workflow_actions()}

    assert any(name.startswith("github/codeql-action/") for name in names)


def test_an_uncomparable_latest_is_a_failed_check_not_an_ok() -> None:
    """`codeql-bundle-v2.26.4` shares no numbering with a pinned `v4.37.9`."""
    packages = freshness.parse_workflow_actions(
        "      - uses: github/codeql-action/init@a35ac6e # v4.37.9\n", "codeql.yml"
    )

    rows = freshness.collect_status(packages, lambda _name: "codeql-bundle-v2.26.4", deferrals={})

    assert rows[0]["check_failed"] is True


def test_only_the_pinned_actions_gate_the_run() -> None:
    """25 upstream pyproject floors made the monthly run permanently red."""
    aged_floor = {
        "name": "typer",
        "minimum": "0.23.0",
        "requirement": "typer>=0.23.0",
        "source": "pyproject.toml",
        "hold": "",
        "kind": "pypi",
        "latest": "0.24.0",
        "outdated": True,
        "check_failed": False,
        "deferred_reason": "",
    }
    aged_action = {
        **aged_floor,
        "name": "actions/checkout",
        "kind": "github-action",
        "source": "codeql.yml",
    }

    assert freshness.gating_rows([aged_floor], []) == []
    assert freshness.gating_rows([aged_floor], [aged_action]) == [aged_action]


def test_pins_in_upstream_owned_workflows_do_not_gate() -> None:
    """`ci.yml` is upstream's; repinning it here would be overwritten next sync."""
    row = {
        "name": "actions/checkout",
        "minimum": "4.2.2",
        "requirement": "actions/checkout@v4.2.2",
        "hold": "",
        "kind": "github-action",
        "latest": "7.0.1",
        "outdated": True,
        "check_failed": False,
        "deferred_reason": "",
    }

    assert freshness.gating_rows([], [{**row, "source": "ci.yml, scorecard.yml"}]) == []
    assert freshness.gating_rows([], [{**row, "source": "ci.yml, codeql.yml"}]) == []
    assert len(freshness.gating_rows([], [{**row, "source": "codeql.yml"}])) == 1


def test_fork_owned_workflows_matches_git() -> None:
    """The constant must not rot when upstream adds a workflow."""
    baseline = json.loads(
        (REPO_ROOT / "tools" / "upstream_baseline.json").read_text(encoding="utf-8")
    )["reviewed_through"]
    listed = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", baseline, "--", ".github/workflows"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if listed.returncode != 0:
        pytest.skip("baseline commit not available in this checkout")
    from_git = {line.rsplit("/", 1)[-1] for line in listed.stdout.splitlines() if line.strip()}

    assert set(freshness.UPSTREAM_WORKFLOWS) == from_git


def test_the_report_says_which_rows_gate() -> None:
    report = freshness.render_markdown([], [])

    assert "informational" in report
    assert "fork-owned rows gate" in report
    assert "`ci.yml`" in report
