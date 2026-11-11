# AI Agent Development Handbook

An engineering handbook for building agentic systems, and the audit skill family that checks a codebase against it.

Two halves that reference each other:

- **The handbook** ([`docs/engineering/`](docs/engineering/README.md)) — normative directives covering the life of a change through ten parts, from problem framing to operation. Prose, meant to be read.
- **The audit skills** ([`.agents/skills/`](.agents/skills)) — the handbook's executable distillate for the subset that can be checked from a repository. Nine domains, 87 check records.

They are joined by the [traceability matrix](docs/audit/handbook-traceability.md), which maps every `##` section of the handbook onto the checks that cover it, and records honestly what is process-only and cannot be audited from a snapshot. Coverage is not chased to 100%; it is chased to 100% *accounted for*.

## Install as a Claude Code plugin

```
/plugin marketplace add mesagroup/ai-agent-development-handbook
/plugin install handbook-audit@mesa-handbook
/reload-plugins
```

Then run `/audit` in any repository for the full sweep, or `/audit <domain>` for one of `arch`, `ci`, `data-protection`, `deps`, `docs`, `eval`, `prompt`, `security`, `test`.

## Working in this repository

```bash
uv sync --group dev

uv run pytest tests/ -q                                        # unit tests
uv run ruff check . && uv run ruff format --check .            # lint
uv run python scripts/render_handbook_traceability.py --check  # integrity gate
uv run python scripts/render_python_fixture_expectations.py --check  # integrity gate
uv run deptry .                                                # dependency hygiene gate
uv run python scripts/render_handbook_traceability.py          # regenerate the matrix Markdown
uv run python scripts/render_handbook_artifact.py              # render the handbook to one HTML file
uv run python scripts/check_handbook_citations.py   # every citation a report emits resolves to an anchor in the page
uv run python scripts/emit_audit_issues.py <findings.json> --target <owner/repo>  # dry-run the issue set a sweep would file
```

The matrix Markdown is generated. Edit [`handbook-traceability.yaml`](docs/audit/handbook-traceability.yaml), never the `.md`.

The traceability gate is the one that matters most: the matrix and the check records are two views of a single edge set, and a change applied to only one of them fails it. Rendering the handbook artifact additionally needs the [`d2`](https://d2lang.com) CLI on `PATH`.

## Licence

This repository, the handbook text included, is released under the [MIT License](LICENSE). The typefaces under [`fonts/`](fonts/) are not: each family carries its own SIL Open Font License in its directory.

## History

This repository was extracted from its origin repository with history preserved, so `#NNN` references in commits before the split point at that repository's issues and read as `<origin-repo>#NNN`. `CLAUDE.md` says what that placeholder stands for; the origin's name lives in the engagement's own records, not here.
