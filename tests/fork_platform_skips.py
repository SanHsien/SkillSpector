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

"""SanHsien fork plugin: report tests the product cannot run on this platform as skipped.

Since 2.12.0 the product writes report files only where ``O_NOFOLLOW`` and ``dir_fd``
are available, and refuses ``--output`` elsewhere (Windows) with one fixed message.
Upstream's CLI tests assume POSIX and write reports to files, so on Windows they fail
with that refusal instead of exercising what they test.

This plugin turns exactly those failures into skips, and only when the capability
probe says secure file output is missing. Any other failure, or this message on a
platform that does support secure output, is left as a failure. Loaded by
``tools/dev_check.ps1`` with ``-p tests.fork_platform_skips``; upstream files are not
modified.
"""

from __future__ import annotations

import pytest

from tests.platform_support import (
    SECURE_FILE_OUTPUT,
    SECURE_FILE_OUTPUT_REFUSAL,
    SKIP_NO_SECURE_FILE_OUTPUT,
    SKIP_NO_SYMLINK,
    SYMLINKS_SUPPORTED,
)

# Windows caps one environment variable at 32,767 characters. Some upstream tests
# are parametrized with whole payloads, so ``PYTEST_CURRENT_TEST`` (node id + stage)
# overflows and pytest errors before the test runs. The variable is informational
# only; cap it so those tests run here.
_ENV_VALUE_LIMIT = 32_000
_ERROR_PRIVILEGE_NOT_HELD = 1314  # Windows: symlink creation without the privilege

_REFUSED_KEY = pytest.StashKey[bool]()


def _install_recorder(item: pytest.Item) -> list[tuple[object, str, object]]:
    """Wrap every loaded reference to the product's refusal check for this test."""
    import sys

    from skillspector import file_output

    original = file_output.require_secure_file_output

    def recording() -> None:
        try:
            original()
        except ValueError:
            item.stash[_REFUSED_KEY] = True
            raise

    patched: list[tuple[object, str, object]] = []
    for module in list(sys.modules.values()):
        if getattr(module, "require_secure_file_output", None) is original:
            patched.append((module, "require_secure_file_output", original))
            module.require_secure_file_output = recording
    return patched


def _platform_skip_reason(
    item: pytest.Item, report: pytest.TestReport, call: pytest.CallInfo[None]
) -> str | None:
    if not report.failed:
        return None
    text = " ".join(str(report.longrepr).split())
    if not SECURE_FILE_OUTPUT:
        # Subprocess-based tests cannot be observed in-process; fall back to the
        # product's exact refusal text in the failure report.
        if item.stash.get(_REFUSED_KEY, False) or SECURE_FILE_OUTPUT_REFUSAL in text:
            return SKIP_NO_SECURE_FILE_OUTPUT
    excinfo = call.excinfo
    if (
        not SYMLINKS_SUPPORTED
        and excinfo is not None
        and isinstance(excinfo.value, OSError)
        and getattr(excinfo.value, "winerror", None) == _ERROR_PRIVILEGE_NOT_HELD
        and any(
            entry.name == "symlink_to" or entry.name == "symlink" for entry in excinfo.traceback
        )
    ):
        return SKIP_NO_SYMLINK
    return None


def pytest_configure(config: pytest.Config) -> None:
    from _pytest import runner

    original = runner._update_current_test_var

    def capped(item: pytest.Item, when) -> None:
        if when and len(item.nodeid) + 16 > _ENV_VALUE_LIMIT:
            import os

            os.environ["PYTEST_CURRENT_TEST"] = f"{item.nodeid[:_ENV_VALUE_LIMIT]}... ({when})"
            return
        original(item, when)

    runner._update_current_test_var = capped


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item: pytest.Item, nextitem: pytest.Item | None):
    patched = [] if SECURE_FILE_OUTPUT else _install_recorder(item)
    try:
        yield
    finally:
        for module, name, value in patched:
            setattr(module, name, value)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[None]):
    outcome = yield
    report: pytest.TestReport = outcome.get_result()
    reason = _platform_skip_reason(item, report, call) if report.when in {"setup", "call"} else None
    if reason is not None:
        report.outcome = "skipped"
        report.longrepr = (str(item.path), item.location[1] or 0, f"Skipped: {reason}")
