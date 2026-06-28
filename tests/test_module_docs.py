"""Behaviour: every custom Ansible module ships valid, parseable documentation
(ansible-doc must render it). Guards against malformed DOCUMENTATION YAML."""
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
MODULES = sorted(p.stem for p in (REPO / "library").glob("*.py"))

pytestmark = pytest.mark.skipif(
    shutil.which("ansible-doc") is None, reason="ansible-doc not installed"
)


@pytest.mark.parametrize("module", MODULES)
def test_module_documentation_renders(module):
    proc = subprocess.run(
        ["ansible-doc", "-t", "module", module],
        capture_output=True, text=True, cwd=str(REPO),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert module.upper() in proc.stdout
