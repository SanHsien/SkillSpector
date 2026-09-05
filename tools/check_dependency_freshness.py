"""Compare declared dependency floors against their current upstream releases.

This fork declares Python dependencies in `pyproject.toml` (`[project.dependencies]`
plus every `[project.optional-dependencies]` group -- `mcp`, `langgraph-dev`, `dev`)
and pins third-party GitHub Actions in `.github/workflows/*.yml`. Dependabot proposes
upgrades one pull request at a time, which answers "is there a newer release?" but
never "how far behind is what we declare, across every declaration in the repo?".
This reads both sources, asks PyPI (for the Python packages) and the GitHub Releases
API (for the Actions) for the current release, and writes a Markdown report.

It compares declarations only. Nothing here inspects the installed environment (the
`uv.lock` resolution) and nothing here edits `pyproject.toml` or a workflow: a newer
release is a prompt to read the changelog and run the suite, not a merge.

    python tools/check_dependency_freshness.py --output report.md --github-output
"""

from __future__ import annotations

import argparse
import json
import os
import re
import tomllib
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "skillspector-dependency-freshness"

PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

_NAME_RE = re.compile(r"^([A-Za-z0-9_.][A-Za-z0-9_.-]*)(?:\[[^\]]*\])?\s*(.*)$")
_MINIMUM_RE = re.compile(r"(>=|>|==|~=)\s*([0-9][0-9A-Za-z.!+_-]*)")
_RELEASE_RE = re.compile(r"^[0-9]+(?:\.[0-9]+)*")
_USES_RE = re.compile(
    r"^\s*(?:-\s*)?uses:\s*([\w.\-]+/[\w.\-]+)@([0-9a-fA-F]{40}|\S+)"
    r"(?:\s*#\s*(.*))?\s*$",
    re.MULTILINE,
)
# One dependency literal per line is how this repo's pyproject.toml is formatted
# today (see [project].dependencies and every [project.optional-dependencies]
# group). A single-line array would lose hold support silently -- an acceptable
# trade against hand-parsing TOML comments, which tomllib does not expose.
_LINE_LITERAL_RE = re.compile(r'^\s*"([^"]+)"\s*,?\s*(?:#\s*(.*))?\s*$')
HOLD_MARKER = "freshness-hold:"
DEFERRALS_PATH = REPO_ROOT / ".github" / "dependency-deferrals.json"
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"


class DependencyCheckError(RuntimeError):
    """Raised when pyproject.toml or the workflows directory cannot be read."""


def release_key(version: str) -> tuple[int, ...] | None:
    """Return the numeric release segment of a version, or None if unparsable.

    Pre-release and local suffixes are dropped, so 7.0.0rc1 and 7.0.0 rank the
    same. That is precise enough to answer "has the declared floor aged?"
    without adding a PEP 440 or semver parser to a repo whose declared
    dependencies are a handful of PyPI packages and pinned GitHub Actions.
    """
    match = _RELEASE_RE.match(version.strip().lstrip("vV"))
    if not match:
        return None
    return tuple(int(part) for part in match.group(0).split("."))


def is_newer_version(latest: str, declared: str) -> bool:
    """Is `latest` newer than `declared` at the precision `declared` states?

    A floor of `Pillow>=10` says nothing about the minor, so reporting 10.4.0
    against it would be a standing false alarm -- and a monthly report that
    cries wolf gets ignored. The comparison therefore happens at the depth the
    declaration commits to: `>=10` on the major alone, `>=1.26` on major.minor,
    and `v7.0.1` on all three segments for a pinned Action.
    """
    latest_key = release_key(latest)
    declared_key = release_key(declared)
    if latest_key is None or declared_key is None:
        return False
    depth = len(declared_key)
    padded = latest_key + (0,) * (depth - len(latest_key))
    return padded[:depth] > declared_key


def load_deferrals(path: Path = DEFERRALS_PATH) -> dict[str, tuple[str, str]]:
    """Read reviewed-but-not-now decisions: package -> (reviewed release, reason).

    A hold says "this floor is the floor we want" and never expires. A deferral
    says "we looked, and not this month", which is a different claim and must
    not outlive the release it was made against. `deferredLatest` is what makes
    it expire by itself: once the upstream source moves past that release the
    report asks again, so a deferral cannot quietly become a permanently
    silenced check. An entry without it is ignored for exactly that reason.

    The file is optional: a fork with no live deferrals need not carry one.
    """
    try:
        entries = json.loads(path.read_text(encoding="utf-8")).get("deferrals", {})
    except (OSError, ValueError):
        return {}
    deferrals: dict[str, tuple[str, str]] = {}
    for name, entry in (entries or {}).items():
        if not isinstance(entry, dict):
            continue
        latest = str(entry.get("deferredLatest", "")).strip()
        reason = str(entry.get("reason", "")).strip()
        if latest and reason:
            deferrals[name.lower()] = (latest, reason)
    return deferrals


def _is_self_reference(name: str, project_name: str) -> bool:
    """`skillspector[mcp]` inside the `dev` extra names this project, not a dependency."""
    normalize = lambda value: value.lower().replace("_", "-")  # noqa: E731
    return bool(project_name) and normalize(name) == normalize(project_name)


def _line_hold_comments(text: str) -> dict[str, str]:
    """Map each quoted dependency literal to its trailing `# freshness-hold:` comment."""
    holds: dict[str, str] = {}
    for line in text.splitlines():
        match = _LINE_LITERAL_RE.match(line)
        if not match:
            continue
        literal, comment = match.group(1), (match.group(2) or "").strip()
        if comment.startswith(HOLD_MARKER):
            holds[literal] = comment[len(HOLD_MARKER) :].strip()
    return holds


def parse_dependency_spec(spec: str, source: str, hold: str) -> dict[str, str] | None:
    head = spec.split(";", 1)[0].strip()
    match = _NAME_RE.match(head)
    if not match:
        return None
    name, specifiers = match.groups()
    minimum = _MINIMUM_RE.search(specifiers)
    return {
        "name": name,
        "minimum": minimum.group(2) if minimum else "",
        "requirement": spec,
        "source": source,
        "hold": hold,
        "kind": "pypi",
    }


def load_direct_dependencies(root: Path = REPO_ROOT) -> list[dict[str, str]]:
    """`[project.dependencies]` plus every `[project.optional-dependencies]` group.

    Self-references such as `skillspector[mcp]` inside the `dev` extra name this
    project's own package, not an external dependency, and are skipped.
    """
    path = root / "pyproject.toml"
    if not path.is_file():
        raise DependencyCheckError("missing pyproject.toml")
    text = path.read_text(encoding="utf-8")
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise DependencyCheckError(f"invalid pyproject.toml: {exc}") from exc

    project = data.get("project", {})
    if not isinstance(project, dict):
        raise DependencyCheckError("pyproject.toml has no [project] table")
    project_name = str(project.get("name", ""))
    holds = _line_hold_comments(text)

    groups: list[tuple[str, list[str]]] = [
        ("project.dependencies", list(project.get("dependencies", None) or []))
    ]
    optional = project.get("optional-dependencies") or {}
    for extra, specs in optional.items():
        groups.append((f"project.optional-dependencies.{extra}", list(specs or [])))

    packages: list[dict[str, str]] = []
    seen: set[str] = set()
    for source, specs in groups:
        for spec in specs:
            head = spec.split(";", 1)[0].strip()
            name_match = _NAME_RE.match(head)
            if not name_match:
                continue
            name = name_match.group(1)
            if _is_self_reference(name, project_name):
                continue
            key = name.lower().replace("_", "-")
            if key in seen:
                continue
            package = parse_dependency_spec(spec, source, holds.get(spec, ""))
            if package is None:
                continue
            seen.add(key)
            packages.append(package)
    return packages


def parse_workflow_actions(text: str, source: str) -> list[dict[str, str]]:
    """Every `uses: owner/repo@<ref> # vX.Y.Z` declaration in a workflow file."""
    packages: list[dict[str, str]] = []
    for match in _USES_RE.finditer(text):
        action, ref, comment = match.group(1), match.group(2), (match.group(3) or "").strip()
        hold = comment[len(HOLD_MARKER) :].strip() if comment.startswith(HOLD_MARKER) else ""
        # A pinned SHA carries its declared version in the trailing comment
        # (`# v7.0.1`); an unpinned floating tag (`@v4`) carries it in the ref
        # itself. Either is a real declaration worth tracking -- only a hold
        # or a comment/ref with no parseable number leaves `minimum` empty.
        version_source = comment if comment else ref
        version_match = _RELEASE_RE.match(version_source.lstrip("vV")) if not hold else None
        minimum = version_match.group(0) if version_match else ""
        packages.append(
            {
                "name": action,
                "minimum": minimum,
                "requirement": f"{action}@{comment or ref[:12]}",
                "source": source,
                "hold": hold,
                "kind": "github-action",
            }
        )
    return packages


def load_workflow_actions(root: Path = REPO_ROOT) -> list[dict[str, str]]:
    """Every pinned Action across `.github/workflows/*.yml`, deduplicated.

    The same action pinned to the same declared version in two files is one
    row with both sources listed; pinned to two *different* declared versions
    it is two rows, because that split is itself drift worth seeing.
    """
    workflows_dir = root / ".github" / "workflows"
    if not workflows_dir.is_dir():
        raise DependencyCheckError("missing .github/workflows directory")
    merged: dict[tuple[str, str], dict[str, str]] = {}
    for path in sorted(workflows_dir.glob("*.yml")):
        text = path.read_text(encoding="utf-8")
        for package in parse_workflow_actions(text, path.name):
            key = (package["name"].lower(), package["minimum"] or package["requirement"])
            existing = merged.get(key)
            if existing is None:
                merged[key] = package
                continue
            sources = existing["source"].split(", ")
            if path.name not in sources:
                sources.append(path.name)
                existing["source"] = ", ".join(sources)
    return sorted(merged.values(), key=lambda p: (p["name"], p["minimum"]))


def fetch_pypi_version(package_name: str, timeout: float = 10.0) -> str | None:
    quoted_name = urllib.parse.quote(package_name, safe="")
    request = urllib.request.Request(
        f"https://pypi.org/pypi/{quoted_name}/json",
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError):
        return None
    version = payload.get("info", {}).get("version")
    return str(version) if version else None


def fetch_github_release(action_name: str, timeout: float = 10.0) -> str | None:
    quoted_name = urllib.parse.quote(action_name, safe="/")
    request = urllib.request.Request(
        f"https://api.github.com/repos/{quoted_name}/releases/latest",
        headers={"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError):
        return None
    tag = payload.get("tag_name")
    return str(tag).lstrip("vV") if tag else None


def collect_status(
    packages: list[dict[str, str]],
    fetch: Callable[[str], str | None],
    deferrals: dict[str, tuple[str, str]] | None = None,
) -> list[dict[str, object]]:
    deferrals = deferrals if deferrals is not None else load_deferrals()
    rows: list[dict[str, object]] = []
    for package in packages:
        minimum = package["minimum"]
        latest = fetch(package["name"])
        reviewed, reason = deferrals.get(package["name"].lower(), ("", ""))
        deferred = bool(reviewed and latest and not is_newer_version(latest, reviewed))
        rows.append(
            {
                **package,
                "latest": latest or "unknown",
                "outdated": bool(minimum and latest and is_newer_version(latest, minimum)),
                "check_failed": not minimum or latest is None,
                "deferred_reason": reason if deferred else "",
            }
        )
    return rows


def needs_review(row: dict[str, object]) -> bool:
    """An aged floor still counts unless a hold or a live deferral covers it."""
    return bool(row["outdated"]) and not row.get("hold") and not row.get("deferred_reason")


def _render_table(rows: list[dict[str, object]]) -> list[str]:
    lines = [
        "| Package | Declared in | Requirement | Latest | Status |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        if row["check_failed"]:
            status = "CHECK FAILED"
        elif row.get("hold") and row["outdated"]:
            status = f"HELD: {row['hold']}"
        elif row.get("deferred_reason") and row["outdated"]:
            status = f"DEFERRED at {row['latest']}: {row['deferred_reason']}"
        elif row["outdated"]:
            status = "REVIEW UPDATE"
        else:
            status = "OK"
        lines.append(
            f"| `{row['name']}` | `{row['source']}` | `{row['requirement']}` | "
            f"`{row['latest']}` | {status} |"
        )
    if not rows:
        lines.append("| - | - | - | - | CHECK FAILED |")
    return lines


def render_markdown(
    rows_python: list[dict[str, object]],
    rows_actions: list[dict[str, object]] | None = None,
    error: str | None = None,
) -> str:
    rows_actions = rows_actions if rows_actions is not None else []
    lines = ["# Dependency freshness report", ""]
    if error:
        lines.extend(["## Check failed", "", f"```text\n{error}\n```", ""])
        return "\n".join(lines)

    lines.extend(["## Python dependencies (pyproject.toml, via PyPI)", ""])
    lines.extend(_render_table(rows_python))
    lines.append("")
    lines.extend(["## GitHub Actions (pinned in .github/workflows/)", ""])
    lines.extend(_render_table(rows_actions))
    lines.extend(
        [
            "",
            "Declared ranges are compared against PyPI (Python dependencies in",
            "pyproject.toml) and the GitHub Releases API (pinned Actions). The",
            "resolved `uv.lock` environment is not inspected and no file is edited",
            "by this check.",
            "",
            "## Review policy",
            "",
            "0. A red line has exactly two honest exits, and both leave a reason behind:",
            "   `# freshness-hold: <why>` on the declaring line for a standing policy, or",
            "   an entry in `.github/dependency-deferrals.json` with `deferredLatest` for",
            "   \"reviewed, not now\" -- that one expires by itself once the upstream source",
            "   moves past the release it was reviewed against. Raising the declared floor",
            "   to silence the report is not one of them: the declaration is a compatibility",
            "   promise, not a mute button.",
            "1. Read the release notes, and check the supported Python versions.",
            "2. Run `pwsh tools/dev_check.ps1` before widening a Python range.",
            "3. Repin a GitHub Action by its new commit SHA with a `# vX.Y.Z` comment; do",
            "   not switch a pinned SHA back to a floating tag.",
            "",
        ]
    )
    return "\n".join(lines)


def write_github_output(
    rows_python: list[dict[str, object]],
    rows_actions: list[dict[str, object]],
    report_path: Path,
) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    rows = rows_python + rows_actions
    outdated = any(needs_review(row) for row in rows)
    check_failed = not rows or any(bool(row["check_failed"]) for row in rows)
    with open(output_path, "a", encoding="utf-8") as output:
        output.write(f"outdated={'true' if outdated else 'false'}\n")
        output.write(f"check_failed={'true' if check_failed else 'false'}\n")
        output.write(f"needs_attention={'true' if outdated or check_failed else 'false'}\n")
        output.write(f"report_path={report_path.as_posix()}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="dependency-freshness-report.md")
    parser.add_argument(
        "--github-output",
        action="store_true",
        help="Write status fields to GITHUB_OUTPUT",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero when a declared range has aged.",
    )
    args = parser.parse_args()

    rows_python: list[dict[str, object]] = []
    rows_actions: list[dict[str, object]] = []
    error: str | None = None
    try:
        deferrals = load_deferrals()
        rows_python = collect_status(load_direct_dependencies(), fetch_pypi_version, deferrals)
        rows_actions = collect_status(load_workflow_actions(), fetch_github_release, deferrals)
    except DependencyCheckError as exc:
        error = str(exc)

    report = render_markdown(rows_python, rows_actions, error)
    output_path = Path(args.output)
    output_path.write_text(report, encoding="utf-8")
    print(report)

    if args.github_output:
        write_github_output(rows_python, rows_actions, output_path)
    if error:
        return 2
    if args.strict and any(
        needs_review(row) or bool(row["check_failed"]) for row in rows_python + rows_actions
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
