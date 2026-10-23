"""Hold the vendored `analyze_prompt.py` to its source and to the route that runs it (#234).

`prompt/cognitive-load`'s command route runs the `prompt-analyzer` skill's
quantitative scan from a copy this plugin carries. Three things can go wrong
with a copy, and none of them is visible from the record:

- **The copy drifts.** An edit made here, even a linter's, turns it into a
  fork nobody decided to maintain. `VENDORED.md` records the source commit and
  the hash of the file taken from it, and the hash is held here, so a local
  edit fails the suite and an update has to restate both.
- **The route stops naming it.** The argv spells the path under
  `${CLAUDE_PLUGIN_ROOT}`; a path that resolves to nothing in this checkout
  resolves to nothing in the plugin cache either.
- **The scan stops producing what the note promises.** The route's note names
  the metrics a run reads, and a script that runs cleanly while emitting none
  of them is a clean-looking result with nothing in it.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from audit_checks import SKILLS_DIR, load_checks

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".agents" / "skills" / "prompt-audit" / "scripts"
VENDORED = SCRIPTS / "analyze_prompt.py"
PROVENANCE = SCRIPTS / "VENDORED.md"
PLUGIN_ROOT = "${CLAUDE_PLUGIN_ROOT}"

PROMPT = """# Assistant

## Role

You MUST answer the question. You SHOULD cite a source. See Steps.

## Steps

1. You MUST read the input.
2. You MUST NOT guess.
"""


def _route():
    checks, errors = load_checks(SKILLS_DIR)
    assert errors == []
    (route,) = [
        r for r in checks["prompt/cognitive-load"].routes if r.kind == "command"
    ]
    return route


def _recorded(field: str) -> str:
    match = re.search(
        rf"^\| {re.escape(field)} \| `([^`]+)` \|$",
        PROVENANCE.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    assert match, f"{PROVENANCE.name} records no {field}"
    return match.group(1)


def test_the_copy_is_the_file_its_provenance_names():
    digest = hashlib.sha256(VENDORED.read_bytes()).hexdigest()
    assert digest == _recorded("SHA-256")
    assert re.fullmatch(r"[0-9a-f]{40}", _recorded("Source commit"))


def test_the_route_runs_the_vendored_copy_through_the_interpreter():
    route = _route()
    assert route.own_runner is True
    assert route.argv[0] == "python3"
    assert route.argv[1] == f"{PLUGIN_ROOT}/{VENDORED.relative_to(REPO_ROOT)}"
    assert route.applies_when is None


def test_the_route_as_written_reports_the_metrics_its_note_names(tmp_path):
    prompt = tmp_path / "prompt.md"
    prompt.write_text(PROMPT, encoding="utf-8")
    argv = [sys.executable if token == "python3" else token for token in _route().argv]
    argv = [token.replace(PLUGIN_ROOT, str(REPO_ROOT)) for token in argv]
    argv = [str(prompt) if token == "<file>" else token for token in argv]
    result = subprocess.run(
        [*argv, "--format", "json"], capture_output=True, text=True, check=True
    )
    report = json.loads(result.stdout)
    assert report["est_tokens"] > 0
    assert report["grand_total_directives"] == 4
    steps = {s["id"]: s for s in report["sections"]}["Steps"]
    assert steps["directives"] == {"MUST": 1, "MUST NOT": 1}
    assert "constraint_lines" in steps
    for field in ("cross_reference_graph", "data_flow_depth", "redundancy_groups"):
        assert field in report, field
