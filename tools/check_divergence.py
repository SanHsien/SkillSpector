# SPDX-FileCopyrightText: Copyright (c) 2026 SanHsien
# SPDX-License-Identifier: Apache-2.0
"""Check that docs/DIVERGENCE.md matches every changed upstream-owned file."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = REPO_ROOT / "tools" / "upstream_baseline.json"
DIVERGENCE_PATH = REPO_ROOT / "docs" / "DIVERGENCE.md"
RENAME_ALIASES = {"README.en.md": "README.md"}
ROW = re.compile(r"^\|\s*`([^`]+)`")


class DivergenceError(RuntimeError):
    """The divergence check could not obtain complete evidence."""


def registered_paths(text: str) -> set[str]:
    """Read only the first column of the canonical divergence table."""
    in_registry = False
    result: set[str] = set()
    for line in text.splitlines():
        if line.strip() == "## 分岔清單":
            in_registry = True
            continue
        if in_registry and line.startswith("## "):
            break
        if in_registry and (match := ROW.match(line.strip())):
            result.add(match.group(1).strip())
    if not in_registry:
        raise DivergenceError("docs/DIVERGENCE.md has no '## 分岔清單' section")
    return result


def divergent_paths(pairs: list[tuple[str, str]], owned: set[str]) -> set[str]:
    """Return upstream path names changed by the fork."""
    result: set[str] = set()
    for status, path in pairs:
        if status in {"M", "D"} and path in owned:
            result.add(path)
        elif status == "A" and path in RENAME_ALIASES:
            upstream_path = RENAME_ALIASES[path]
            if upstream_path in owned:
                result.add(upstream_path)
    return result


def git(repo: Path, *args: str) -> str:
    process = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if process.returncode:
        raise DivergenceError(process.stderr.strip() or f"git {' '.join(args)} failed")
    return process.stdout


def collect(repo: Path, baseline_path: Path) -> tuple[str, set[str]]:
    try:
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DivergenceError(f"invalid baseline: {exc}") from exc
    base = baseline.get("reviewed_through")
    if not isinstance(base, str) or len(base) != 40:
        raise DivergenceError("baseline reviewed_through must be a full 40-character SHA")
    git(repo, "cat-file", "-e", f"{base}^{{commit}}")
    owned = set(git(repo, "ls-tree", "-r", "--name-only", base).splitlines())
    pairs: list[tuple[str, str]] = []
    # Disable rename detection so a renamed upstream-owned file is reported as a
    # deletion of its original path plus a fork-owned addition.  Otherwise the
    # R status could bypass the M/D/A registry mapping below.
    for line in git(repo, "diff", "--no-renames", "--name-status", base, "--").splitlines():
        if line.strip():
            parts = line.split("\t")
            pairs.append((parts[0][0], parts[-1]))
    return base, divergent_paths(pairs, owned)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-dir", type=Path, default=REPO_ROOT)
    parser.add_argument("--baseline", type=Path, default=BASELINE_PATH)
    parser.add_argument("--divergence-doc", type=Path, default=DIVERGENCE_PATH)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        base, actual = collect(args.repo_dir, args.baseline)
        registered = registered_paths(args.divergence_doc.read_text(encoding="utf-8"))
    except (OSError, DivergenceError) as exc:
        print(f"divergence check failed: {exc}")
        return 2
    missing = sorted(actual - registered)
    stale = sorted(registered - actual)
    result = {
        "base_commit": base,
        "changed_upstream_files": sorted(actual),
        "registered_files": sorted(registered),
        "changed_but_not_registered": missing,
        "registered_but_not_changed": stale,
    }
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"{len(actual)} upstream file(s) diverge; {len(registered)} registered.")
        for label, paths in (
            ("Changed but not registered", missing),
            ("Stale registry row", stale),
        ):
            for path in paths:
                print(f"{label}: {path}")
        if not missing and not stale:
            print("OK: divergence registry matches the working tree.")
    return 1 if missing or stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
