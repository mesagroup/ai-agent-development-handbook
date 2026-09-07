# CLAUDE.md

## Commands

```bash
uv sync --group dev
git config core.hooksPath .githooks   # once per clone; git does not do it for you
uv run pytest tests/ -q
uv run ruff check . && uv run ruff format --check .
uv run python scripts/render_handbook_traceability.py --check   # integrity gate
uv run python scripts/render_handbook_traceability.py           # regenerate the matrix Markdown
uv run python scripts/render_handbook_artifact.py               # needs the d2 CLI
uv run python scripts/render_python_fixture_expectations.py --check   # integrity gate
uv run python scripts/render_python_fixture_expectations.py           # regenerate the fixture expectations
uv run python scripts/build_python_fixtures.py --all                  # generate the five gitignored fixture trees
```

Run `ruff check` AND `ruff format --check` before committing. CI runs both.

`.githooks/commit-msg` refuses a commit message carrying an AI attribution trailer, and `core.hooksPath` is what makes git run it, so a fresh clone that skips that line has the rule in prose only. The rule itself is that no commit in this repository carries one, and it is a hook rather than a convention because prose was not enough: a harness injected an attribution instruction mid-session, declaring that it superseded earlier attribution guidance, and six commits were written with the trailer before anyone reading the log noticed the branch had changed convention. The hook names the assistant rather than the `Co-Authored-By` key, so a human co-author trailer still works; it matches only at the start of a line and skips comment lines, so a message discussing the convention is not caught by mentioning it; and a deliberate exception is `--no-verify`.

## Repository layout

- `docs/engineering/` — the handbook. Normative prose, ten parts.
- `docs/audit/handbook-traceability.yaml` — the matrix. Source of truth.
- `docs/audit/handbook-traceability.md` — generated. Never edit it; edit the YAML and re-render.
- `docs/audit/sweep-obligations.md` — hand-maintained, unlike its neighbour: one row per `audit-core` obligation, recording how the `audit` sweep discharges it. Editing `audit-core/SKILL.md` or `audit/SKILL.md` means checking it. `tests/test_sweep_obligations.py` catches a row whose anchor no longer occurs in `audit-core` exactly once, a quotation that is no longer verbatim, and a row that has slipped out of the checked set; it cannot judge whether a disposition is still true, which is a reading pass over the whole of `audit-core`.
- `docs/audit/python-fixture-expectations.md` — generated. Never edit it; edit `scripts/python_fixture_spec.py` and re-render. The seeded fixture trees and this record come from that one module on purpose: expectations kept in a second file are free to drift, and a seed present in the tree but missing from the expectations reads exactly like a tool that correctly found nothing.
- `.agents/skills/` — the audit skill family: `audit`, `audit-core`, and nine `<domain>-audit` skills.
- `.agents/skills/<domain>-audit/checks/<slug>.md` — one check record per auditable check.

## Plugin

This repository ships as a Claude Code plugin (`.claude-plugin/`). Three things read as oversights and are deliberate:

- `plugin.json` declares no `version`. Claude Code then falls back to the git commit SHA, so every install tracks every push. Adding a version pins consumers to it.
- `"skills": "./.agents/skills/"` is a custom path. Moving the tree to a conventional `skills/` means editing `SKILLS_DIR` in two scripts, every check record's path, the test fixtures and the integrity gate.
- `claude plugin validate` checks the manifest and does not enumerate skills, so it passes on a plugin that discovers none. `claude plugin details handbook-audit` does print the skill count — but it reads the **installed marketplace clone** under `~/.claude/plugins/marketplaces/`, which tracks a pushed commit and is usually behind. So it cannot see a skill added on an unmerged branch, and reporting its count as this branch's is how a working skill gets called undiscovered (or a broken one gets called fine). Two sound checks instead: `uv run python -c "import sys; sys.path.insert(0, 'scripts'); from audit_checks import SKILLS_DIR, load_checks; c, e = load_checks(SKILLS_DIR); print(len(c), e)"` proves the records parse from *this* tree, and the running session's own available-skills list names a newly written skill within a turn or two of the `SKILL.md` landing, which is the only live evidence that its frontmatter parses as a skill rather than as a file. Re-run `claude plugin details` after the merge, where it is the right tool.

The repository is private, so the absolute GitHub URLs the skills emit resolve only for members of the owning organisation. Audit reports handed to an outside reader will carry links that reader cannot open.

## Task management

This repository uses the `github-issues-workflow` skill. An issue per unit of work, a branch named `<number>-short-description`, `status:*` labels tracking progress, `Refs #<number>` in commit messages, and a PR that closes the issue. Never merge without explicit approval.

The `status:*` labels exist in the repository and are not decorative: move the issue as the work moves, removing the previous status before adding the next.

## Issue references and provenance

The handbook, the skill family and this tooling were extracted from `lidia-tech/lidia-agents` with `git filter-repo`; that repository keeps the build record and the PRs. Write an issue that lives there as `lidia-tech/lidia-agents#NNN` and one that lives here as `#NNN`. Commit messages already follow this, so a bare number in history is a number in this repository.

Path-based history surgery matches *historical* paths. A file renamed out of a directory needs that directory in the allowlist or its history truncates at the rename, with no error to tell you.

## Toolchain

- ruff's `extend-exclude = ["docs"]` is load-bearing. Recent ruff formats Python inside Markdown fences, and specs, plans and stories are a record of what was written at the time; reformatting their samples edits that record.
- `scripts/render_handbook_artifact.py` imports `markdown` lazily, so a missing dependency surfaces when the renderer runs rather than at import. It is declared in `pyproject.toml`; a lazy import is not a reason to leave one undeclared.
- The artifact renderer reports `residual .md hrefs: 0`. A relative `.md` link out of the handbook tree (only `engineering-notes.md` today) is *unlinked* rather than mapped - it prints a `NOTE`, keeps the link text and drops the anchor, because a self-contained page cannot link to a file it does not contain. A *sibling* `.md` link naming no part still raises.
- Diagrams need the `d2` CLI.

## Check records

Every check is one Markdown file with YAML frontmatter: `id` (`<domain>/<slug>`), `domain`, `locality` (`local` or `global`), `handbook` (list of matrix row ids, may be empty), `handbook_note` (required when `handbook` is empty), `optin` (default false), an optional `evidence` carrying what the check measures and what a row records as its evidence, where that belongs to the check rather than to any one route, and one of two mutually exclusive schemas naming what the check runs - a record carrying both is rejected. The legacy schema is `tooling` (optional), `needs` (optional; maps `resolved-tree` or `target-execution` to tool names drawn from `tooling`) and `ungranted_note` (required exactly where every tool in some language carries a tier, rejected as vacuous elsewhere). The routes schema is `routes` (optional, and rejected empty where present; a list of mappings, each one way of answering the check in one language, carrying `lang`, `kind`, `tool`, an optional `package` where the installable differs from the tool's name, `argv` (required on `kind: command`, rejected on every other kind), `argv_by_partition` (a mapping of partition name to that partition's own command, where a target's partitions split along more than the tool invocation itself - a python route's partitions are `uv`, `pip`, `poetry`, `pipenv` and `pylock`, and only four of those name a package manager), `then` (a second command the record prescribes in sequence, where it does - `coverage run -m pytest` followed by `coverage report --show-missing` is one route rather than two, and dropping the half that prints the report leaves a route that looks like a tool which produced nothing), `own_runner` (the prescribed command is complete as written, so whatever one-shot runner a lens would put in front of it puts nothing: `true` where every command the route prescribes needs none, its shared `argv` and its per-partition overrides alike, or the partitions whose override needs none where the rest do - `false` and an empty list are both rejected rather than read as the default, because an absent key already says the launcher applies, so writing the field is a claim, and each of those two is that claim spelled as nothing at all), `disposition`, `needs`, `in_env`, `findings_stream`, `applies_when`, `alone_insufficient` and `note`) and `answers_ungranted` (`ungranted_note`'s counterpart: the sentinel `none`, required wherever a language's every answering-kind route needs a grant and none stays untiered). A record declaring `routes` carries no `## Tooling fallback` section and the loader rejects one: the routes are the fallback there, and a section beside them is a second copy nothing holds against the first. A migrated record's `tooling` and `needs` are derived from its routes by projection, so a consumer reading those two fields sees the same shape regardless of which schema the record declares - but the projection carries the tools and their tiers and carries no ungranted claim at all, so whether a withheld grant silences a language is never derived from the projected pair on a migrated record. That question is decided over the record's answering-kind, non-`forbidden` routes, where a `kind: subject` route neither gives a language a claim to silence nor supplies one's escape, and the projection keeps such a route's tool with its tier - which is how a language every route in was only ever inspecting the check's subject reads through the pair as fully tiered.

A record declaring neither `tooling` nor `routes` must state in its body what to read instead.

`needs` is the second axis on a tooling name, on a record still declaring `tooling` directly rather than `routes`. `tooling` says where a tool comes from; `needs` says what must be present in the target before it answers - nothing beyond a read-only clone by default, a materialized dependency graph for `resolved-tree`, that plus running the target's own code for `target-execution`. The names repeat those in `tooling` on purpose and the validator checks the repetition, so a rename that misses one of the two places fails the gate. An omitted tier is a positive claim that no tool here needs it, which is why a record left unclassified reads as clean rather than as unfinished. Two guards in `tests/scripts/test_audit_checks.py` bound that, each covering what the other cannot: `test_a_tool_has_one_tier_across_the_family` catches a tool two records classify differently, and `test_the_classification_is_not_vacuous` holds the number of records carrying `needs` at the number the classification sweep produced, so removing a key fails the suite instead of quietly reading as the default. What neither can see is a record that was never examined and genuinely needs a tier — the first is silent unless another record already classified the same tool, and the second only counts. That one is a reading pass. A route states the same tier directly as its own `needs` field, one axis on the route itself rather than a second mapping kept in step with a first.

`ungranted_note` is the third claim on a record still declaring `tooling`, and it is about the check rather than about a tool. `needs` says what each tool requires; the engine turns that into a conclusion about the check — every tool needs a grant, so a withheld grant means `no-evidence` — and that derivation is wrong wherever the check has an axis needing no tool. Five records had resorted to contradicting their own frontmatter in prose before this field existed. It is required on exactly the records the rule would silence and rejected as vacuous elsewhere, so absence is never a silent claim the way an absent `needs` tier still is. The value is either what still answers or the sentinel `none`; the loader rejects `None`, `NONE`, `null` and an empty value by name, because YAML turns the first two into ordinary strings that read as a fallback claim and the last two into nothing at all. `tests/scripts/test_audit_checks.py` holds a floor on how many records say something real, which is the only guard against satisfying the requirement with `none` everywhere — it cannot tell a correct `none` from a lazy one. `answers_ungranted` is this field's counterpart on a record declaring `routes`, required by the same rule applied per route rather than per tool: a `kind: subject` route never counts toward a language's claim to silence, and a `disposition: forbidden` route never counts as its escape.

A `tooling` list, on a record declaring `tooling` rather than `routes`, holds candidates for the language, not commands guaranteed to run on a given partition - at most one package-manager subcommand in it applies to any one partition, and `## Tooling fallback` states which and in what order. Every candidate must still be something *some* partition in that language can run, which is one of three kinds: a registry package a one-shot runner can fetch, a subcommand of the target's own package manager, or a standalone binary in no language registry. Only the first is fetchable, so an entry of the second or third kind that the record does not distinguish gets attempted as a package, fails like a missing tool, and reports `no-evidence` for a check that could have been answered. Never name one ecosystem's package manager as if it were the language's - `npm audit` is not the JavaScript audit command, it is npm's, and it resolves from a lockfile a pnpm or yarn target does not have. Where the kinds differ across package managers, `## Tooling fallback` states the precedence and names the ecosystem-neutral option. Verify a name against the tool's own documentation, not against whether a fetch succeeds: the unscoped `cyclonedx-npm` resolves to a dependency-confusion placeholder rather than to the CycloneDX generator, which is `@cyclonedx/cyclonedx-npm`, so a runner fetches it, runs it, and produces nothing - indistinguishable from a tool that ran and found nothing. A route names its kind directly - `command`, `library`, `procedure` or `subject` - and states precedence as its `disposition` and its position among the record's routes, so neither depends on `## Tooling fallback` prose there.

Every review-lens paragraph carries a `**Label** - ` prefix.

## Matrix and records are one edge set

A matrix row's `checks:` entry and a record's `handbook:` entry are the two directions of the same edge. Change one, change the other, or the gate fails. Add the citation and the row in the same commit.

Where a consistency property can move out of prose and into the validator, move it.

## Writing

- Markdown is never hard-wrapped: one paragraph is one source line. Never reflow lines you did not change.
- No em-dash (U+2014) in `docs/engineering/`, `docs/superpowers/specs/`, `docs/superpowers/plans/`. Use ` - `.
- Never commit environment-specific values: absolute personal paths, profile names, tokens, hostnames, emails. Use `<placeholder>` and say what it resolves to.
- Links in `.agents/skills/` to files in this repo are absolute GitHub URLs, because the skills run from a plugin cache in other repositories where a relative path resolves to nothing. Everything under `docs/` links relatively: those files are read in the repo or on GitHub, the plugin does not ship them (`plugin.json` points only at `.agents/skills/`), and an absolute URL bakes the org and repo name into every report and artifact the file is copied into.

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

Mutation checks against `scripts/run_python_fixture_lens.py` run with `PYTHONDONTWRITEBYTECODE=1`. `.pyc` invalidation compares the source's mtime and size, and some of the mutations this table invites move a token between fields without changing either, so a mutate-run-revert inside one second can leave the next run honouring the mutant's cached bytecode. It shows up as a failure on a byte-identical clean tree, or, in the direction that matters, as a green run over a mutation that should have failed. A mutation that does change the file's length is not exposed to it, which is why the instruction is the flag rather than a judgement about each mutation.

## Errors

No bare `except Exception: pass`. Every exception is reported to the caller with type and message, logged at the right level, or re-raised.
