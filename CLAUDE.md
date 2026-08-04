# CLAUDE.md

## Commands

```bash
uv sync --group dev
uv run pytest tests/ -q
uv run ruff check . && uv run ruff format --check .
uv run python scripts/render_handbook_traceability.py --check   # integrity gate
uv run python scripts/render_handbook_traceability.py           # regenerate the matrix Markdown
uv run python scripts/render_handbook_artifact.py               # needs the d2 CLI
```

Run `ruff check` AND `ruff format --check` before committing. CI runs both.

## Repository layout

- `docs/engineering/` — the handbook. Normative prose, nine parts.
- `docs/audit/handbook-traceability.yaml` — the matrix. Source of truth.
- `docs/audit/handbook-traceability.md` — generated. Never edit it; edit the YAML and re-render.
- `.agents/skills/` — the audit skill family: `audit`, `audit-core`, and eight `<domain>-audit` skills.
- `.agents/skills/<domain>-audit/checks/<slug>.md` — one check record per auditable check.

## Check records

Every check is one Markdown file with YAML frontmatter: `id` (`<domain>/<slug>`), `domain`, `locality` (`local` or `global`), `handbook` (list of matrix row ids, may be empty), `handbook_note` (required when `handbook` is empty), `tooling` (optional), `optin` (default false).

A record omitting `tooling` must state what to read instead.

Every review-lens paragraph carries a `**Label** - ` prefix.

## Matrix and records are one edge set

A matrix row's `checks:` entry and a record's `handbook:` entry are the two directions of the same edge. Change one, change the other, or the gate fails. Add the citation and the row in the same commit.

Where a consistency property can move out of prose and into the validator, move it.

## Writing

- Markdown is never hard-wrapped: one paragraph is one source line. Never reflow lines you did not change.
- No em-dash (U+2014) in `docs/engineering/`, `docs/superpowers/specs/`, `docs/superpowers/plans/`. Use ` - `.
- Never commit environment-specific values: absolute personal paths, profile names, tokens, hostnames, emails. Use `<placeholder>` and say what it resolves to.
- Handbook and skill links to files in this repo are absolute GitHub URLs. The skills run from a plugin cache in other repositories, where a relative path resolves to nothing.

## Prose about the code — write claims that cannot go stale

- Name a thing, don't number it: "the `checks` argument", not "the fourth argument".
- State the structural reason, not the current snapshot.
- Never assert a count you did not compute. Compute it in the same breath, or state no number.
- Avoid claims about a sibling ("every other check does X"). Verify as you write, or rephrase so the claim is local.

## Stale-prose pass — scope by blast radius, not by the diff

Before pushing, make one pass for prose the change invalidated **without touching**. Do not scope it to the diff.

- Removed or renamed a symbol, parameter or field? `grep` for its name and for the prose describing it.
- Changed what a fixture or helper produces? `grep` for its name and read every comment near a caller.
- Changed a shape, invariant or default? Read the whole file, not the hunk.

Dispatch it to a subagent that has not seen the implementation.

## Tests

New code ships with unit tests, and adding code must not lower coverage. Scripts are not exempt: load them with `importlib.util.spec_from_file_location` and exercise their pure helpers, with `scripts/` on `sys.path` via `tests/scripts/conftest.py`.

## Errors

No bare `except Exception: pass`. Every exception is reported to the caller with type and message, logged at the right level, or re-raised.
