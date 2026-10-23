# Vendored files

Two files under this skill are byte-identical copies of the `prompt-analyzer` skill's, taken from `<prompt-analyzer-source>`, the group's skills repository that ships that skill, whose name lives in the group's own records and never here.

| Path | Source path | Source commit | SHA-256 |
|---|---|---|---|
| `scripts/analyze_prompt.py` | `skills/prompt-analyzer/scripts/analyze_prompt.py` | `c620050f2b62307679e6bb11d73b2cd4331494de` | `05b6c524f8899a9df577dc93c84cec25f4544102db7dfcd6f2aa0417114201f4` |
| `references/analysis-framework.md` | `skills/prompt-analyzer/references/analysis-framework.md` | `f01e7b0c816da9beaf8a27462d6864dd23d24d62` | `a9a6bbb16ff6e8dd50c87b282b0eb259a9031754b182d61ca6d661d8ce3aa4bf` |

- **`scripts/analyze_prompt.py`** is the quantitative scan. `prompt/cognitive-load`'s command route runs it as `python3 ${CLAUDE_PLUGIN_ROOT}/.agents/skills/prompt-audit/scripts/analyze_prompt.py <file>`, so the scan is available wherever this plugin is installed rather than only on a target that ships the skill. It imports only the standard library, so the audit host's own Python 3 runs it and nothing is fetched. It is run through the interpreter because it is not tracked as executable.
- **`references/analysis-framework.md`** is the framework that interprets the scan's numbers, and the one `SKILL.md`'s opt-in sub-agent decomposition and reasoning-token deliverables apply.

The copies are not edited here, not even to satisfy this repository's linters or writing conventions, which is why `pyproject.toml` excludes the script from ruff: a byte-identical copy is what lets `tests/test_vendored_prompt_analyzer.py` hold each file's hash against the table above, so a local edit fails the suite rather than drifting silently from the source. To update one, copy it again from a newer source commit and change its commit and hash above in the same commit.
