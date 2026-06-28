import sys
from pathlib import Path

# Make the repo-root `tooling` package importable in tests.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Ansible module_utils live as plain modules; expose them for direct unit tests.
sys.path.insert(0, str(REPO_ROOT / "module_utils"))

# Filter plugins are plain modules too; expose for direct unit tests.
sys.path.insert(0, str(REPO_ROOT / "filter_plugins"))
