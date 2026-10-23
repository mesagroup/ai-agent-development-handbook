# Vendored: `analyze_prompt.py`

`analyze_prompt.py` is a byte-identical copy of the `prompt-analyzer` skill's quantitative scan, taken from `<prompt-analyzer-source>`, the group's skills repository that ships that skill, whose name lives in the group's own records and never here.

| Field | Value |
|---|---|
| Source path | `skills/prompt-analyzer/scripts/analyze_prompt.py` |
| Source commit | `c620050f2b62307679e6bb11d73b2cd4331494de` |
| SHA-256 | `05b6c524f8899a9df577dc93c84cec25f4544102db7dfcd6f2aa0417114201f4` |

`prompt/cognitive-load`'s command route runs it as `python3 ${CLAUDE_PLUGIN_ROOT}/.agents/skills/prompt-audit/scripts/analyze_prompt.py <file>`, so the scan is available wherever this plugin is installed rather than only on a target that ships the skill. It imports only the standard library, so the audit host's own Python 3 runs it and nothing is fetched. It is run through the interpreter because it is not tracked as executable.

The copy is not edited here, not even to satisfy this repository's linters, which is why `pyproject.toml` excludes it from ruff: a byte-identical copy is what lets `tests/test_vendored_prompt_analyzer.py` hold its hash against the table above, so a local edit fails the suite rather than drifting silently from the source. To update it, copy the file again from a newer source commit and change the commit and the hash above in the same commit.
