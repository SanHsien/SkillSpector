[CmdletBinding()]
param(
    [switch]$Quick
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repoRoot

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

function Invoke-Step {
    param(
        [Parameter(Mandatory)]
        [string]$Label,
        [Parameter(Mandatory)]
        [string]$Exe,
        [Parameter(Mandatory)]
        [string[]]$Arguments
    )

    Write-Host "==> $Label"
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE"
    }
}

# Canonical gate for this fork. Upstream's Makefile is POSIX sh (uses `command -v`,
# `rm -rf`, `find`), which does not run on native Windows (non-WSL2). This script
# bypasses the Makefile entirely and calls `uv` / `ruff` / `pytest` directly instead
# of wrapping `make` targets.
Invoke-Step -Label "Ruff check" -Exe "uv" -Arguments @(
    "run", "ruff", "check", "src/", "tests/", "tools/check_divergence.py", "tools/check_pin_bounds.py"
)
Invoke-Step -Label "Ruff format --check" -Exe "uv" -Arguments @(
    "run", "ruff", "format", "--check", "src/", "tests/", "tools/check_divergence.py", "tools/check_pin_bounds.py"
)
Invoke-Step -Label "Version smoke test" -Exe "uv" -Arguments @("run", "skillspector", "--version")
Invoke-Step -Label "Divergence registry" -Exe "uv" -Arguments @(
    "run", "python", "tools/check_divergence.py"
)
Invoke-Step -Label "Locked dependency bounds" -Exe "uv" -Arguments @(
    "run", "python", "tools/check_pin_bounds.py"
)

# Non-strict on purpose: this reports declared-dependency drift for a human to
# read (dependency-freshness-report.md), it does not gate the commit on PyPI /
# GitHub Releases being reachable from this machine right now.
Invoke-Step -Label "Dependency freshness check" -Exe "uv" -Arguments @(
    "run", "python", "tools/check_dependency_freshness.py",
    "--output", "dependency-freshness-report.md"
)

if ($Quick) {
    Write-Host "WINDOWS DEV CHECK GREEN (-Quick: skipped pytest)"
    return
}

# `integration` and `provider` tests may call live LLM endpoints and need credentials;
# they are excluded here the same way pyproject.toml's default `addopts` excludes them.
Invoke-Step -Label "Pytest" -Exe "uv" -Arguments @("run", "pytest", "-m", "not integration and not provider", "tests/", "-q")

Write-Host "WINDOWS DEV CHECK GREEN"
