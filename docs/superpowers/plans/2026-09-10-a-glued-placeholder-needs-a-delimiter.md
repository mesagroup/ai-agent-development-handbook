# Plan: the form extractor's three escapes

Issue #56. Design: [../specs/2026-09-10-a-glued-placeholder-needs-a-delimiter-design.md](../specs/2026-09-10-a-glued-placeholder-needs-a-delimiter-design.md).

In the order that keeps each step's failure legible: close the false-clean hole first, then make the shape it forbids say so, then the fence convention, then the prose limit.

## 1. `_marked` requires a value delimiter, and the tests inject both degenerate cases

`tests/scripts/test_python_fixture_harness.py`. A token ending in `<` is a mark only where the character before it is `=`, `:` or `/`. `_matches` then falls through to exact equality for anything else, so `-r<` no longer accepts `-rf` and `-<` no longer accepts every flag in existence.

The new assertions cover both cases #56 names - `-r<` against `-rf`, and `-<` against an unrelated flag - because a fix tested only on the first has not shown the mark cannot degenerate. Both were run against the pre-fix code and observed to fail; the spec's table records what they returned.

`_matches`' docstring loses the sentence that reads as though this hole were already closed. It says the mark is what keeps the test from being a blanket prefix test, illustrated with `-r` and `-rf`, which is the unmarked path and is true of it - and #56 points out it reads as coverage of the marked path.

## 2. A record-level guard refuses the shape the matcher now rejects

Same module. A glued placeholder whose head does not end in `=`, `:` or `/` is unverifiable, so the guard fails on it by name rather than leaving the coverage property to report a missing token about a token the record did write.

Its floor is the tree's own count, which is zero, so it fires on the first such token rather than on a number someone has to keep current.

## 3. `scripts/audit_checks.py` rejects a fenced code block in a record body

Beside the `## Tooling fallback`-beside-`routes:` rejection, which is the same kind of rule and the precedent for where it lives. Both fence spellings, and the message names what the convention is for and that an indented block showing a tool's output is not what it forbids.

A test in `tests/scripts/test_audit_checks.py` in both directions: a record carrying a fence is rejected, and the tree's 77 records still load with no errors, which is what says the rule states a convention already kept rather than demanding a migration.

## 4. The prose limit gets a durable home

The accepted limit goes in the extractor's module docstring, where a reader of the extractor meets it, and the convention it rests on goes in `CLAUDE.md`'s check-record section, where a record author reads what a record may contain.

## Gates

All six, plus a mutation check in both directions on the delimiter rule: with the rule reverted the two new assertions must fail, and with the guard's condition inverted the guard must fail. `PYTHONDONTWRITEBYTECODE=1` on those runs, because a mutate-run-revert inside one second can otherwise leave the next run honouring the mutant's cached bytecode.
