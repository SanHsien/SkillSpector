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

"""Runtime capability probes for tests that need POSIX-only filesystem features.

These are probes, not platform checks. A Windows host with Developer Mode enabled
can create symlinks, so the suite must decide from what the process can actually do
rather than from ``sys.platform``.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

HAS_MKFIFO = hasattr(os, "mkfifo")
"""``os.mkfifo`` exists (POSIX). Windows has no named-pipe equivalent in ``os``."""

HAS_GETEUID = hasattr(os, "geteuid")
"""``os.geteuid`` exists (POSIX). Windows has no numeric effective user id."""


def _probe_symlinks() -> bool:
    """Return whether this process may create a filesystem symlink."""
    try:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "target"
            target.write_text("probe", encoding="utf-8", newline="\n")
            (root / "link").symlink_to(target)
    except (OSError, NotImplementedError):
        return False
    return True


SYMLINKS_SUPPORTED = _probe_symlinks()
"""Symlink creation succeeds. False on Windows without Developer Mode or admin."""


def _probe_shebang_exec() -> bool:
    """Return whether an extensionless shebang script on PATH runs by bare name.

    Tests that stub an external CLI (``gh``, say) write a ``#!/usr/bin/env python3``
    file and prepend its directory to PATH. Windows' ``CreateProcessW`` appends only
    ``.exe`` when a command has no extension, so the stub is never found and the real
    CLI runs instead -- or nothing does.
    """
    import subprocess

    try:
        with tempfile.TemporaryDirectory() as raw:
            bin_dir = Path(raw)
            script = bin_dir / "skillspector_probe_cli"
            script.write_text(
                "#!/usr/bin/env python3\nprint('ok')\n", encoding="utf-8", newline="\n"
            )
            script.chmod(0o755)
            env = dict(os.environ, PATH=f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
            result = subprocess.run(
                ["skillspector_probe_cli"],
                env=env,
                capture_output=True,
                text=True,
                # The CLI writes UTF-8; the default locale codec is cp950 on some
                # Windows hosts and raises UnicodeDecodeError in the reader thread.
                encoding="utf-8",
                timeout=30,
            )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and result.stdout.strip() == "ok"


SHEBANG_CLI_STUBS_SUPPORTED = _probe_shebang_exec()
"""An extensionless shebang script on PATH is executable by bare name."""

SKIP_NO_MKFIFO = "named pipes are unavailable on this platform"
SKIP_NO_SYMLINK = "symlink creation is unavailable to this process"
SKIP_NO_GETEUID = "os.geteuid is unavailable on this platform"
SKIP_NO_SHEBANG_CLI = "PATH stubs written as shebang scripts are not executable here"

BACKSLASH_IS_FILENAME_CHAR = "\\" not in {os.sep, os.altsep}
"""A backslash is an ordinary file-name character. False on Windows, where it separates paths."""

SKIP_BACKSLASH_IS_SEPARATOR = (
    "a backslash separates paths on this platform, so it cannot sit inside a file name"
)


def _probe_secure_file_output() -> bool:
    """Return whether the product's symlink-safe report writer is available here."""
    from skillspector import file_output

    return bool(file_output._SECURE_OUTPUT_SUPPORTED)


SECURE_FILE_OUTPUT = _probe_secure_file_output()
"""The product writes report files only where ``O_NOFOLLOW`` and ``dir_fd`` exist.

On other platforms (Windows) ``--output`` is refused by design and the user is told to
redirect stdout, so tests that exercise file output cannot run there.
"""
SKIP_NO_SECURE_FILE_OUTPUT = (
    "the product refuses report file output on this platform (no O_NOFOLLOW/dir_fd)"
)
SECURE_FILE_OUTPUT_REFUSAL = "Safe file output is unsupported on this platform"
"""The exact refusal the product raises; tests failing only with it are untestable here."""


def _probe_exec_bits() -> bool:
    """Return whether clearing the execute bits makes ``os.access(X_OK)`` false."""
    try:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "probe"
            target.write_text("", encoding="utf-8")
            target.chmod(0o644)
            return not os.access(target, os.X_OK)
    except OSError:
        return False


EXEC_BITS_ENFORCED = _probe_exec_bits()
"""POSIX execute permission is honoured. Windows reports every existing file as executable."""
SKIP_NO_EXEC_BITS = "execute permission bits are not enforced on this platform"

RMTREE_USES_FD = bool(getattr(__import__("shutil").rmtree, "avoids_symlink_attacks", False))
"""``shutil.rmtree`` walks with directory file descriptors (POSIX); Windows uses a path walk."""
SKIP_NO_FD_RMTREE = "shutil.rmtree does not use the fd-based walk on this platform"


def _probe_env_case_sensitive() -> bool:
    """Return whether environment variable names differ by case."""
    key = "SKILLSPECTOR_CASE_PROBE"
    os.environ[key] = "upper"
    try:
        return os.environ.get(key.lower()) != "upper"
    finally:
        os.environ.pop(key, None)


ENV_KEYS_CASE_SENSITIVE = _probe_env_case_sensitive()
"""POSIX keeps ``HTTPS_PROXY`` and ``https_proxy`` apart; Windows folds them into one."""
