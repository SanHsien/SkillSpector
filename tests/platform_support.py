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
