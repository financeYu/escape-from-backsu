from __future__ import annotations

import re
import shutil
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent
SANDBOX_TMP_ROOT = PROJECT_ROOT / "tests" / "_tmp" / "pytest_tmp_path"


@pytest.fixture
def tmp_path(request: pytest.FixtureRequest) -> Iterator[Path]:
    """Sandbox-friendly replacement for pytest's built-in tmp_path fixture.

    Pytest creates its basetemp directory with restrictive permissions. In the
    Codex Windows sandbox those directories can be written but not scanned
    again, so tests fail during fixture setup or session cleanup. Creating
    per-test directories with the default Windows ACL keeps validation local to
    the ignored tests/_tmp tree while avoiding that sandbox-specific failure.
    """

    SANDBOX_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    safe_name = _safe_node_name(request.node.nodeid)
    path = SANDBOX_TMP_ROOT / f"{safe_name}-{uuid.uuid4().hex[:12]}"
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def _safe_node_name(nodeid: str) -> str:
    name = re.sub(r"[^A-Za-z0-9_.-]+", "_", nodeid).strip("._")
    return name[:80] or "pytest_tmp_path"
