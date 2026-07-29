---
name: test-audit
description: "Audit a Python project's automated tests: line/branch coverage and its gaps on load-bearing logic, TDD adherence (does new/changed deterministic code ship with tests), test quality (assertion strength, over-mocking, tautologies), and flakiness/determinism. Use before trusting the suite as a safety net, when coverage has drifted or a bug slipped through green tests, after a big feature, or when the user asks to audit tests / coverage / test quality. Works on any Python project. Runs on the audit-core engine. Behavioral/model-level evals belong to eval-audit; this skill owns deterministic code-level tests."
---

# Test Audit (coverage, TDD adherence, test quality)

A domain specialization of **[audit-core](../audit-core/SKILL.md)** — read that first; it owns the loop (scope → parallel evidence → findings matrix → plan → subagent-driven fixes → review → PR) and the cross-cutting rules. This skill supplies the testing lens for **deterministic, code-level tests**. Behavioral, model-level quality — LLM/agent evals, prompt quality, smoke tests — belongs to **`eval-audit`** (a sibling in the audit-skills program); this skill cross-links it rather than covering it.

**Core principle:** a test suite's value is not its coverage percentage — it is whether it *fails when the code breaks*. A high number produced by tests that assert nothing, mock the thing under test, or never exercise the hard branches is a false safety net that is worse than an honest low number. The audit measures both reach (coverage) and strength (does a test actually catch a regression), and treats a confident-but-weak suite as a finding.

**Announce:** "I'm using the test-audit skill (on the audit-core engine) to audit the test suite."

## When to use

- Before relying on the suite as a merge safety net, or after a bug slipped through with tests green (a sign of weak assertions or an uncovered branch).
- When coverage has drifted down, or a large feature landed and you want to know what it left untested.
- When tests are flaky, slow, or order-dependent and eroding trust in CI.
- When the user asks to audit tests, coverage, test quality, or TDD adherence.

**Not for:** LLM/agent behavioral evaluation, prompt auditing, or smoke tests (use `eval-audit`); nor writing a project's first test suite from scratch (that's authoring — though the audit's gap list seeds it).

## 1. Subject & scope

The test suite and the production code it is meant to protect. Establish first:

- **The test layout + runner** — where tests live, the framework (`pytest` / `unittest`), markers, and how the suite is invoked (including what CI runs vs. what is excluded by default, e.g. integration markers).
- **What coverage is claimed / required** — any coverage floor the contributor guide or CI enforces, and the "new code ships with tests / don't lower coverage" rule if the project states one.
- **The deterministic core vs. I/O edges** — the pure logic (parsing, scoring, transforms, id-mapping, verdict application) that *must* be tested, versus S3/network/LLM edges that may be mocked or left to integration tests. The deterministic core is where gaps matter most.

Slice the parallel evidence pass **by package/module** — one read-only agent per slice — so each maps its production units, the tests that cover them, and the coverage/quality of those tests.

## 2. Dimensions (findings-matrix columns)

- **Coverage reach** — line and (crucially) **branch** coverage per module; uncovered load-bearing logic; error/exception paths never exercised. Raw percentage is context, not the finding — an uncovered branch in a scorer is.
- **TDD adherence / new-code coverage** — does new or changed deterministic code ship with tests? Modules that grew without their tests growing; a coverage regression introduced by recent work (measure coverage **on the diff**, not just globally).
- **Assertion strength** — tests that assert nothing, only assert "no exception raised," assert against a value the test itself computed the same way (tautology), or over-mock so the real unit never runs. These inflate coverage without catching regressions.
- **Determinism / flakiness** — tests that depend on ordering, wall-clock time, randomness, network, or shared mutable state; tests that pass/fail non-deterministically.
- **Isolation & speed** — unit tests doing real I/O, missing markers (integration masquerading as unit), pathologically slow tests that discourage running the suite.
- **Effectiveness (optional)** — mutation score: do the tests actually kill injected faults (see §7).

## 3. Evidence sources & tooling

**Detect** what the project has (check `pyproject.toml` / config): the runner (`pytest`), coverage (`pytest-cov` / `coverage.py`), diff-coverage (`diff-cover`), flakiness/order tools (`pytest-randomly`, `pytest-rerunfailures`), timeouts (`pytest-timeout`), property-based testing (`hypothesis`), and mutation (`mutmut` / `cosmic-ray`). Prefer a tool the project already runs; fall back otherwise.

Run in the parallel evidence pass:
- **Coverage (with branches):** `pytest --cov=<pkg> --cov-branch --cov-report=term-missing` (or `coverage run -m pytest` + `coverage report --show-missing`). Branch coverage is the signal; capture the missing line/branch ranges per module as the evidence pointer.
- **Diff coverage:** `diff-cover coverage.xml --compare-branch=origin/main` to find coverage the *current work* added or dropped — this is the TDD-adherence evidence.
- **Assertion-strength review (the load-bearing step):** read the tests covering each high-risk module and judge whether an assertion would actually fail if the code regressed. A scanner can't do this — a subagent reading `test → code` pairs can. Flag no-op asserts, tautologies, and over-mocking with `file:line`.
- **Flakiness:** run the suite in randomized order (`pytest-randomly` randomizes automatically once installed; use `--randomly-seed=<n>` to reproduce a failing order) and, for suspected flakies, repeat runs; flag order-dependence and non-determinism. Grep tests for `time.time()`, `datetime.now()`, `random.` without a seed, and live network calls.
- **Speed/isolation:** `pytest --durations=25` for the slowest tests; check unit tests for real I/O.

Read the contributor guide for the coverage rule and any test-pattern conventions (e.g. how the project tests scripts). Record the coverage metric or `test_file:line` as the evidence pointer for every row.

## 4. Status scale + severity rubric

Status per row: **ok / warn / violation** (coverage: meets-floor / below-floor / untested).

- **Critical** — load-bearing deterministic logic (a scorer's math, an adjudicator's id-mapping, a parser, a security check) with **no** effective test, or covered only by a test that can't fail; a coverage regression that drops below a required floor; a green suite that misses a class of bug because assertions are hollow.
- **Important** — an untested error/branch path in important code; new/changed code that shipped without tests; a flaky test that erodes CI trust; heavy over-mocking that means the unit under test never actually runs.
- **Minor** — a moderately-low-coverage-but-low-risk module, a slow test, a missing marker, a stylistic test-hygiene issue.

Suppressions (an intentionally untested throwaway script, an I/O edge deferred to integration tests) must be explicit and recorded with a reason — never silently dropped. Do not "fix" coverage by asserting nothing; that is the very anti-pattern this audit exists to catch.

## 5. Fix patterns (and CI implications)

Fixes here **add or change test code** (and occasionally make production code testable), so they are **not** docs-only: the domain gate is "the (possibly expanded) suite passes **and** coverage does not drop" — run the normal install + lint/typecheck/test CI with coverage, plus the code-review gate.
- **Cover the gap with a real test:** exercise the actual branch/behavior and assert on the observable outcome, not on a value the test recomputed. Prefer testing the deterministic core directly; mock only true I/O edges.
- **Strengthen a weak test:** replace a no-op/tautological assert with one that would fail on a plausible regression; unwind over-mocking so the real unit executes.
- **De-flake:** inject the clock/seed/randomness as a fixture, remove order dependence and shared mutable state, isolate or mark real-I/O tests.
- **If production code is untestable** (hidden side effects, no seam), a small refactor to introduce a seam is in scope — but it must be behavior-preserving and reviewed.
- **Highest-leverage fix:** wire a coverage floor + **diff-coverage gate** into CI (new code must be covered) so the suite can't silently weaken — this enforces the "don't lower coverage" rule mechanically.
- Docs-only output: the findings report and any update to the contributor guide's testing conventions.

## 6. Review dimensions (Phase-5 specialized reviewers)

- **Assertion strength** — would each new/changed test actually fail if the code it covers regressed? (The single highest-value catch — reject tests that raise coverage without catching bugs.)
- **Coverage honesty** — is the reported gain from real exercised behavior, not from importing code or asserting nothing? Branch coverage, not just line.
- **Determinism** — new tests are order-independent and don't reintroduce clock/random/network flakiness.
- **No behavior change from testability refactors** — any seam added to production code preserves behavior; tests still pass.
- **Scope vs plan** — every planned Critical/Important gap actually addressed; nothing silently dropped or papered over with a weak assert.

## 7. Opt-in sub-audits

- **Mutation testing** — run `mutmut` / `cosmic-ray` on the highest-risk modules to measure whether tests kill injected faults (the truest test-effectiveness signal, but slow) — enable via argument or ask the user; default off for a quick pass, recommend on for a scorer/parser-heavy core.
- **Property-based testing gap** — identify pure functions that would benefit from `hypothesis` property tests over example-based ones — ask the user.
- **Behavioral/eval cross-check** — hand off LLM/agent behavioral quality, prompt auditing, and smoke tests to `eval-audit`; note the handoff.
