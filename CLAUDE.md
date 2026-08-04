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

## Plugin

This repository ships as a Claude Code plugin (`.claude-plugin/`). Three things read as oversights and are deliberate:

- `plugin.json` declares no `version`. Claude Code then falls back to the git commit SHA, so every install tracks every push. Adding a version pins consumers to it.
- `"skills": "./.agents/skills/"` is a custom path. Moving the tree to a conventional `skills/` means editing `SKILLS_DIR` in two scripts, every check record's path, the test fixtures and the integrity gate.
- `claude plugin validate` checks the manifest and does not enumerate skills, so it passes on a plugin that discovers none. Verify discovery with `claude plugin details handbook-audit` and read the skill count.

The repository is private, so the absolute GitHub URLs the skills emit resolve only for members of the owning organisation. Audit reports handed to an outside reader will carry links that reader cannot open.

## Issue references and provenance

The handbook, the skill family and this tooling were extracted from `lidia-tech/lidia-agents` with `git filter-repo`; that repository keeps the build record and the PRs. Write an issue that lives there as `lidia-tech/lidia-agents#NNN` and one that lives here as `#NNN`. Commit messages already follow this, so a bare number in history is a number in this repository.

Path-based history surgery matches *historical* paths. A file renamed out of a directory needs that directory in the allowlist or its history truncates at the rename, with no error to tell you.

## Toolchain

- ruff's `extend-exclude = ["docs"]` is load-bearing. Recent ruff formats Python inside Markdown fences, and specs, plans and stories are a record of what was written at the time; reformatting their samples edits that record.
- `scripts/render_handbook_artifact.py` imports `markdown` lazily, so a missing dependency surfaces when the renderer runs rather than at import. It is declared in `pyproject.toml`; a lazy import is not a reason to leave one undeclared.
- The artifact renderer warns about one unmapped link to `engineering-notes.md`. That link leaves the handbook tree, so there is no in-artifact anchor to map it onto. Expected, not a regression.
- Diagrams need the `d2` CLI.

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

When dispatching any agent from a git worktree, pass the worktree's absolute root and require the agent to confirm `git rev-parse --show-toplevel` matches before it reads or edits. Agents left to infer the path resolve it to the primary checkout instead: a reader then reports evidence from a tree you are not working in, and a writer's edit lands where your `git status` never shows it, so it drops out of the commit and afterwards looks as though the agent simply missed the file.

## Tests

New code ships with unit tests, and adding code must not lower coverage. Scripts are not exempt: load them with `importlib.util.spec_from_file_location` and exercise their pure helpers, with `scripts/` on `sys.path` via `tests/scripts/conftest.py`.

## Errors

No bare `except Exception: pass`. Every exception is reported to the caller with type and message, logged at the right level, or re-raised.
