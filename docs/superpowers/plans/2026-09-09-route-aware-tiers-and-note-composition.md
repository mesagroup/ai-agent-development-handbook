# Plan: the tier reads routes, the enumeration composes notes, and a tool-less route must prescribe

Issues #75, #76, #73. Design: [../specs/2026-09-09-route-aware-tiers-and-note-composition-design.md](../specs/2026-09-09-route-aware-tiers-and-note-composition-design.md).

Three independent rules over one object. They land in three commits so each is reviewable on its own, in the order that keeps the suite green at every step: the loader rule first (it rejects a shape no record has), then the derivation plus its record edit (which move together or the gate fails), then the enumeration.

## 1. #73 - the loader requires a tool-less route's note

`scripts/audit_checks.py`, in `_load_routes`, beside the branch that already refuses a tool-less route of any kind but `procedure`. Fires only where `kind` is `procedure` and `tool` is absent: a tool-less `command` route is already named by that branch, and a second error on one mistake is noise. Rejects an absent, non-string-empty and whitespace-only note alike, since a blank note is the same silence as a missing one.

Message names the record and the route position and says why: the note is the prescription where there is no tool and no argv.

Tests in `tests/scripts/test_audit_checks.py`:
- a constructed record with a tool-less `procedure` route and no note is rejected by name
- the same with a whitespace-only note
- a tool-less `procedure` route *with* a note still loads
- a population guard holding the count of tool-less routes in the tree, so the rule cannot go vacuous by the shape leaving

Docstring of `_load_routes` gains the rule in its validation list. Module docstring's `## Check records` counterpart is CLAUDE.md's, below.

## 2. #75 - the tiered half reads routes, over the routes that name a tool

`scripts/audit_checks.py`: add `_languages_whose_tools_all_need_a_grant(routes)`, a sibling of `_routes_answering_ungranted`. Per language, the answering-kind, non-forbidden routes that name a tool, each language's own plus the universal ones; the language is in the result where there is at least one such route and every one of them carries a tier. Excludes `kind: subject` and `disposition: forbidden` for the reasons `_routes_answering_ungranted` gives, and excludes a language naming no tool for the reason `_fully_tiered_languages` gives.

Its docstring must distinguish it from `_silenced_languages`, since both read tiers off answering routes and both could be described as mirroring `_fully_tiered_languages`. The distinction is the subject: `_silenced_languages` asks whether anything answers, this asks whether any *tool* answers, and the two together give the three states the spec names.

`tests/scripts/test_python_fixture_spec.py`: `test_the_ungranted_answer_is_stated_exactly_where_the_grant_changes_it` reads the tiered half from the new helper on a migrated record and keeps `_fully_tiered_languages`' reading on a legacy one. Its docstring currently argues two of three conditions are schema-neutral; that claim is what this changes, so it is rewritten rather than extended.

`.agents/skills/deps-audit/checks/inventory.md`: the `cyclonedx-py environment` route declares `needs: resolved-tree`. Its note already says the command answers nothing on a read-only clone, so no prose changes.

Tests in `tests/scripts/test_audit_checks.py`:
- the uneven-tier case: one tool, two routes, one tiered - the language is absent from the new helper's result and present in `_fully_tiered_languages`' reading of the projected pair. This is the case that changed, stated as the two disagreeing.
- a `kind: subject` route's untiered tool does not keep a language out of the result
- a `disposition: forbidden` route's untiered tool does not either
- an untiered universal route naming a tool does keep it out, for every language the record answers for
- a language whose answering routes name no tool at all is absent

Plus a guard holding the eight expectations for which `differs` is true, so the derivation cannot silently drop one.

## 3. #76 - the enumeration composes the prescribed routes' notes

`scripts/run_python_fixture_lens.py`, in `routed_invocations`, replacing the `len(routes) == 1` branch and its raise:

- candidates are the group's `disposition: runs` routes, or every route in the group where none is `runs`
- one candidate contributes its note unchanged
- several contribute each note prefixed by its `applies_when` where it has one, joined by a blank line
- the raise fires where the composition is empty, naming check and tool

The docstring's `Raises:` clause and its one-row-per-`(check, tool)` paragraph both state the rule and why merging into one route was rejected, which is the acceptance criterion #76 asks for.

Tests in `tests/scripts/test_python_fixture_harness.py`:
- a synthetic record whose group has two `runs` routes with `applies_when` composes both notes, each carrying its precondition
- the same with no `applies_when` composes both notes bare
- a `procedure: runs` beside a `command: alternative` takes the `runs` route's note alone
- a group with no `runs` route falls back and takes its single route's note
- a group whose candidates carry no note raises by name
- an identity guard naming the three multi-route no-command groups in the tree, so the shape cannot leave silently
- the existing rows' notes are unchanged, which is what proves the live tree untouched

## 4. Prose and gates

`CLAUDE.md`'s `## Check records` paragraph states #73's requirement, in its own voice and as one source line.

Stale-prose pass, dispatched to a subagent that has not seen the implementation, over: `note`, `applies_when`, `ungranted_note`, `answers_ungranted`, `_fully_tiered_languages`, `_silenced_languages`, `_routes_answering_ungranted`, `routed_invocations`, and the docstring in `test_python_fixture_spec.py` that argues schema-neutrality.

Then `uv run pytest tests/ -q`, both integrity gates, `ruff check`, `ruff format --check`, and the two computations the spec names as the real verification: the set of expectations for which `differs` is true, and every routed row's note.
