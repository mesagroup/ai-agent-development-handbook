"""Put ``scripts/`` on ``sys.path`` so tests can import sibling script helpers.

``render_handbook_traceability.py`` imports ``audit_checks`` as a top-level
module, which resolves at runtime because ``scripts/`` is ``sys.path[0]`` but
not under pytest. Append it here - at conftest import, before collection - so
the import works while the test module is being loaded.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.append(str(_SCRIPTS_DIR))
