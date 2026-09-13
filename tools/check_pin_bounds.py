# SPDX-FileCopyrightText: Copyright (c) 2026 SanHsien
# SPDX-License-Identifier: Apache-2.0
"""Verify every direct dependency resolved in uv.lock satisfies pyproject.toml."""

from __future__ import annotations

import argparse
import json
import re
import tomllib
from pathlib import Path

from packaging.requirements import InvalidRequirement, Requirement
from packaging.version import InvalidVersion, Version

REPO_ROOT = Path(__file__).resolve().parents[1]
NAME_SEPARATORS = re.compile(r"[-_.]+")


class PinBoundsError(RuntimeError):
    """The dependency declarations or lock data are incomplete."""


def normalize(name: str) -> str:
    return NAME_SEPARATORS.sub("-", name).lower()


def load_toml(path: Path) -> dict:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise PinBoundsError(f"{path.name}: {exc}") from exc


def direct_requirements(pyproject: dict) -> list[Requirement]:
    project = pyproject.get("project") or {}
    values = list(project.get("dependencies") or [])
    for group in (project.get("optional-dependencies") or {}).values():
        values.extend(group)
    result: list[Requirement] = []
    for value in values:
        try:
            requirement = Requirement(value)
        except InvalidRequirement as exc:
            raise PinBoundsError(f"unparsable requirement {value!r}: {exc}") from exc
        if normalize(requirement.name) != "skillspector":
            result.append(requirement)
    return result


def locked_versions(lock: dict) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for package in lock.get("package") or []:
        name, version = package.get("name"), package.get("version")
        if isinstance(name, str) and isinstance(version, str):
            result.setdefault(normalize(name), set()).add(version)
    return result


def find_violations(
    requirements: list[Requirement], locked: dict[str, set[str]]
) -> list[dict[str, str]]:
    violations: list[dict[str, str]] = []
    for requirement in requirements:
        name = normalize(requirement.name)
        versions = locked.get(name)
        if not versions:
            violations.append({"package": name, "kind": "missing", "declared": str(requirement)})
            continue
        for raw_version in sorted(versions):
            try:
                accepted = requirement.specifier.contains(Version(raw_version), prereleases=True)
            except InvalidVersion:
                accepted = False
            if not accepted:
                violations.append(
                    {
                        "package": name,
                        "kind": "out-of-range",
                        "locked": raw_version,
                        "declared": str(requirement),
                    }
                )
    return violations


def collect(root: Path = REPO_ROOT) -> tuple[list[Requirement], dict[str, set[str]]]:
    return (
        direct_requirements(load_toml(root / "pyproject.toml")),
        locked_versions(load_toml(root / "uv.lock")),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-dir", type=Path, default=REPO_ROOT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        requirements, locked = collect(args.repo_dir)
    except PinBoundsError as exc:
        print(f"pin bounds check failed: {exc}")
        return 2
    violations = find_violations(requirements, locked)
    result = {"requirements": len(requirements), "violations": violations}
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"{len(requirements)} direct dependency declaration(s) checked.")
        for violation in violations:
            print(f"{violation['kind']}: {violation['package']} ({violation['declared']})")
        if not violations:
            print("OK: every locked direct dependency satisfies its declared bounds.")
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
