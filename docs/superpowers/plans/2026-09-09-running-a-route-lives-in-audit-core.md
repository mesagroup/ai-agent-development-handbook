# Plan: the route-running instruction moves into `audit-core`

Issue #70. Design: [../specs/2026-09-09-running-a-route-lives-in-audit-core-design.md](../specs/2026-09-09-running-a-route-lives-in-audit-core-design.md).

Three commits, in the order that keeps the suite green at every step: the engine gains the section, the sweep gives up its copy, then the obligations ledger records both. The middle commit alone would leave the sweep pointing at a section that does not exist; the third alone would fail `tests/test_sweep_obligations.py` on anchors that are not there yet.

## 1. `audit-core/SKILL.md` gains `## Running a route`

Placed between the loop and `## Authoring a new auditing skill`: run-time instruction is neither a loop step nor an authoring rule, and burying it inside step 1 would put a field-by-field contract inside a bullet about fanning agents out.

Two paragraphs, in this order, because the second refers to the first:

- **The runner and kinds doctrine**, registry-neutral. A `command` route's `argv` is the tool's own command line, so a tool the environment does not carry is fetched by a one-shot runner in front of it - `uvx` or `uv run --with` for PyPI, `npx` for npm - reaching the registry the tool is published in, which a route's `lang` does not name. Then the three kinds a record can name and which one a runner reaches, the import-rather-than-execute case a runner cannot serve at all, and preferring what the inventory reports already installed while recording the resolved version of anything fetched. Names no `dlx` form and no package-manager one-shot, for the reason the design gives.
- **The route contract**, relocated from `audit/SKILL.md`'s routes bullet with its wording intact and two references repointed: `own_runner`'s "the one-shot runner this bullet otherwise requires" names the paragraph above it, and the clause deferring to `ungranted_note`'s scoping "above" names step 1. Check the move by substitution rather than by reading: the relocated paragraph must be byte-identical to the bullet once those two replacements and the list marker are applied.

Step 1's detection-tooling sentence gains a pointer to the section. The anchor `Run the domain's detection/measurement tooling here` stays verbatim - `tests/test_sweep_obligations.py` holds it - so the pointer goes in the parenthesis that follows it.

## 2. `audit/SKILL.md`'s routes bullet becomes a reference

Keeps its first sentence: which schema a record declares, that the migration is partial, and that either can appear. Replaces the contract that followed with a pointer to `audit-core`'s section and one sentence on why the brief does not restate it. The relative link form is the one the file already uses for a sibling skill (`../audit-core/SKILL.md`); an absolute GitHub URL is for `docs/` targets, which the plugin does not ship.

The detection-tooling bullet is not touched, for the reason the design gives, and neither is any other line of the file.

## 3. `docs/audit/sweep-obligations.md` records the new obligations

One row per obligation the new section states, each with a verbatim anchor occurring exactly once in `audit-core/SKILL.md`:

- the route-contract obligations - matching by `lang`, only a `command` route handing you something to run, an unnamed partition meaning no command, `then`, `own_runner`, `disposition`, `alone_insufficient` and `applies_when` - are **delegated**, justified in that disposition's own words.
- the runner obligations - the one-shot runner reaching the tool's registry, the three kinds and which a runner reaches, preferring what is already installed and recording what was fetched - are **restated**, against the sweep's own detection-tooling bullet.

The existing detection-tooling row's justification loses the clause saying the engine does not carry the no-added-dependency constraint, which this change makes false.

## 4. Gates and the prose pass

`uv run pytest tests/ -q`, `ruff check`, `ruff format --check`, both integrity renderers with `--check`, and `tests/test_sweep_obligations.py` read on its own because it is the one this change can break.

Then the stale-prose pass, dispatched to a subagent that has not seen the implementation and given the worktree root to confirm, scoped by which sentence tells an agent where to read the route contract rather than by this change's vocabulary: the nine domain skills' opening paragraphs, `audit/SKILL.md`'s remaining bullets, `CLAUDE.md`'s account of what each file owns, and the specs and plans that describe the split.
