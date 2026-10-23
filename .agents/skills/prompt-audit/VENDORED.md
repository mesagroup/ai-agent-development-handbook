# Origin of the prompt-analyzer files

Two files under this skill began as copies of the `prompt-analyzer` skill's, taken from `<prompt-analyzer-source>`, the group's skills repository that ships that skill, whose name lives in the group's own records and never here. They are maintained here now and are not kept in step with the source.

| Path | Source path | Copied at commit |
|---|---|---|
| `scripts/analyze_prompt.py` | `skills/prompt-analyzer/scripts/analyze_prompt.py` | `c620050f2b62307679e6bb11d73b2cd4331494de` |
| `references/analysis-framework.md` | `skills/prompt-analyzer/references/analysis-framework.md` | `f01e7b0c816da9beaf8a27462d6864dd23d24d62` |

- **`scripts/analyze_prompt.py`** is the quantitative scan. `prompt/cognitive-load`'s command route runs it as `python3 ${CLAUDE_PLUGIN_ROOT}/.agents/skills/prompt-audit/scripts/analyze_prompt.py <file>`, so the scan is available wherever this plugin is installed rather than only on a target that ships the skill. It imports only the standard library, so the audit host's own Python 3 runs it and nothing is fetched. It is run through the interpreter because it is not tracked as executable.
- **`references/analysis-framework.md`** is the framework that interprets the scan's numbers, and the one `SKILL.md`'s opt-in sub-agent decomposition and reasoning-token deliverables apply.
