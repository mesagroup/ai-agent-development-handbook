# Plan: `registry` becomes a route field

Issue #77, closing #28. Design: [../specs/2026-09-09-a-route-names-its-registry-design.md](../specs/2026-09-09-a-route-names-its-registry-design.md).

In the order that keeps the suite green at every step: the loader accepts the field before any record declares it, then the records declare it, then the prose derives the runner from it, then the ledger.

## 1. The loader accepts and validates `registry`

`scripts/audit_checks.py`. `registry` joins `ROUTE_FIELDS` and the `Route` dataclass, parsed beside `package`. Four rules, each with its own error naming the record and the route position:

- rejected on any kind but `command`, since no other kind prescribes a command to front with a runner
- rejected outside the vocabulary `pypi`, `npm`
- rejected beside `own_runner: true`, because that says nothing is fetched
- rejected where it contradicts what `lang` implies (`python` implies `pypi`, `typescript` implies `npm`)
- required where `lang` is `any` or `none`, `kind` is `command`, and `own_runner` is not `true`

Plus `registry_for(route)`, returning the route's own value where it has one and the one `lang` implies otherwise, and `None` where nothing is fetched. One implementation, so a consumer never derives it a second way.

The order matters: the loader has to accept the field before the records declare it, or the middle commit fails the integrity gate.

## 2. The records declare it

`test-audit/checks/new-code-coverage.md`: `registry: pypi` on its only route, which is the hazard #77 is filed against.

`arch-audit/checks/size.md`: the `cloc` route drops `npx` from its argv and declares `registry: npm`; the `wc` route declares `own_runner: true`. Both edits are argued in the design - the first is #78's rejected convention being removed, the second is forced by the required rule and fixes a live defect in the same stroke. Each route's `note` is updated to match, since both notes describe the invocation.

## 3. The prose derives the runner instead of pointing at a note

`audit/SKILL.md`: the runner instruction reads the route's `registry`, falling back to what `lang` implies, and stops telling an agent to read the note "because the field that would say it does not exist yet". The three-kinds paragraph is corrected so the runner comes from the tool's registry rather than the partition's language, which is what closes #28.

`CLAUDE.md`'s record-schema paragraph documents the field beside `package`, in its own voice and as one source line.

## 4. Tests

`tests/scripts/test_audit_checks.py`: one test per rule - each rejection by name, the required case, the accepted case, and `registry_for`'s three outcomes. Plus a population guard holding the number of routes the required rule fires on, so the rule cannot go vacuous by the shape leaving the tree.

## 5. The ledger and the gates

`docs/audit/sweep-obligations.md` gets the reading pass and whatever rows the `audit/SKILL.md` edit earns.

Then `uv run pytest tests/ -q`, `ruff check`, `ruff format --check`, both integrity renderers with `--check`, and the stale-prose pass dispatched to a subagent that has not seen the implementation, given the worktree root to confirm, and scoped by the sentences that choose a runner rather than by this change's vocabulary.
