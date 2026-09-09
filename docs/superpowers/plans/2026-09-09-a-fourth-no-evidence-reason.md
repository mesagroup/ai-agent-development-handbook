# Plan: `not-prescribed` joins the reason vocabulary, in both copies of it

Issue #74. Design: [../specs/2026-09-09-a-fourth-no-evidence-reason-design.md](../specs/2026-09-09-a-fourth-no-evidence-reason-design.md).

In the order that keeps the suite green at every step: the engine's vocabulary first, then the sweep's two sentences, then the record, then the two places the vocabulary is mirrored in code, then the obligations ledger, whose row breaks the moment the engine's sentence changes.

## 1. `audit-core/SKILL.md` gains the reason

Step 2's `no-evidence` paragraph. Four changes inside it, all in one source line:

- the list gains `not-prescribed`, glossed with what would answer it next time (nothing will) and carrying the precedence clause inside the gloss: the record prescribes no command for this partition *and* offers no route a grant would enable.
- "the three ways a check can fail to run" stops naming a count.
- the vocabulary's growth rule is stated - a reason is admissible when it names a genuinely different answer to "what would answer this next time", never where an existing reason is actionable - so the next one is judged rather than argued from a count.
- the closed-scale sentence is marked as being about the **status** scale, which is what its own argument is about.

## 2. `audit/SKILL.md` names it in the two places that decide

The `no-evidence` rendering list in the detection-tooling bullet, and the route-reading sentence that says what a partition the per-partition map does not name is telling you. The second is the one an agent reads with a route in hand, so the precedence clause goes there too rather than only in the vocabulary - tick 1's lesson about scoping by which sentence carries the decision, applied forward.

## 3. `deps-audit/checks/vulnerabilities.md` stops asking for a taxonomy

Its `evidence:` block asks the auditor to distinguish "a retired endpoint and a missing scanner". Those are `tool-failed` and `tool-unavailable`, both already in the vocabulary, so the block names them instead of asking for the distinction to be supplied. The judgement that belongs to the record - which case a retired advisory endpoint is - stays.

## 4. The two mirrors in code

`scripts/run_python_fixture_lens.py`'s `REASONS` stays three, and its comment stops resting on the engine having three: the lens cannot produce this reason, because it observes what a command did and never classifies a check, and the no-command row's `status: ""` is already how it represents the case. `tests/scripts/test_python_fixture_harness.py`'s pin keeps its literal equality and its docstring is rewritten to a justification that survives the engine growing a reason.

## 5. `docs/audit/sweep-obligations.md`

The row anchored on `carries a reason, because the three ways a check can fail to run` no longer matches. It gets a full new anchor rather than a trimmed one, which the test's own docstring forbids. Then a row per obligation the change adds, with the disposition each earns: the sweep restates the reason vocabulary in its fan-out brief, so the reason itself is `restated`; the growth rule governs whoever edits the engine rather than a run, so it is judged on its own.

## 6. A guard for three copies of one vocabulary

One test: the reason names in `audit-core`'s vocabulary sentence and in `audit/SKILL.md`'s rendering sentence are the same set, and `run_python_fixture_lens.REASONS` is that set minus `not-prescribed`. Parsed from the prose rather than hardcoded twice, so the guard cannot pass by agreeing with itself. Mutation-checked by adding a reason to one file only.

## 7. Gates and the prose pass

`uv run pytest tests/ -q`, `ruff check`, `ruff format --check`, both integrity renderers with `--check`, and `tests/test_sweep_obligations.py` read on its own.

Then the stale-prose pass, dispatched to a subagent that has not seen the implementation and given the worktree root to confirm, scoped by the sentences that carry a decision rather than by this change's vocabulary: every place a reason name appears in a check record, every place prose counts the reasons, and the docstrings in `scripts/` that explain what a row's empty status means.
