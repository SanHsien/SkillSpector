# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""SKILLSPECTOR_MAX_STATIC_SECONDS overrides the per-artifact static budget.

Fork-owned feature. Without it the 30-second default is the only ceiling, and an
artifact that sits near it degrades or passes depending on machine load -- which
makes a scan gate built on this scanner report different results for an
unchanged tree. The override exists so a gate can trade wall time for a complete
result; the default is unchanged for everyone who does not set it.
"""

from __future__ import annotations

import importlib

import pytest

MODULE = "skillspector.nodes.analyzers.static_runner"


def _reload_with(monkeypatch: pytest.MonkeyPatch, value: str | None) -> float:
    """Reimport the runner under an env value and return the resulting budget."""
    if value is None:
        monkeypatch.delenv("SKILLSPECTOR_MAX_STATIC_SECONDS", raising=False)
    else:
        monkeypatch.setenv("SKILLSPECTOR_MAX_STATIC_SECONDS", value)
    module = importlib.reload(importlib.import_module(MODULE))
    return module.MAX_STATIC_ANALYSIS_SECONDS_PER_ARTIFACT


@pytest.fixture(autouse=True)
def restore_module_default():
    """Leave the imported module back on its unset-environment default."""
    yield
    import os

    os.environ.pop("SKILLSPECTOR_MAX_STATIC_SECONDS", None)
    importlib.reload(importlib.import_module(MODULE))


def test_unset_environment_keeps_the_shipped_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """No environment variable means the documented 30-second ceiling."""
    assert _reload_with(monkeypatch, None) == 30.0


def test_positive_value_replaces_the_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """A caller can buy more wall time for a large artifact."""
    assert _reload_with(monkeypatch, "600") == 600.0


@pytest.mark.parametrize("value", ["0", "-1"])
def test_non_positive_value_removes_the_ceiling(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    """Zero or negative means "no ceiling", not "expire immediately"."""
    budget = _reload_with(monkeypatch, value)
    assert budget == float("inf")


def test_non_numeric_value_falls_back_to_the_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """A typo must not silently disable or zero out the budget."""
    assert _reload_with(monkeypatch, "not-a-number") == 30.0
