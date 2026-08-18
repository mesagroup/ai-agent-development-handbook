# Closing the harness's one-directional gaps

Design for issue #55. The Python fixture harness records what each check record prescribes separately from what the round had to add to make it run, and that separation is the round's deliverable: a record whose command needs completing is a record to correct. Three ways of moving a token across that line leave the whole suite green while inverting what the round reports. This closes all three, and adds the guard that makes the second of them fail at its first edit rather than its second.

## What is open, and what it costs

Every claim below was measured against the tree at `f89bd62` rather than reasoned about. The harness carries 50 invocations, 33 declared forms of which 7 are declared `alternative` or `superseded`, 13 entries carrying a completion, 25 entries declaring forms, and 1 entry carrying a `then`.

**A prescribed token demoted from `argv` into `completion`.** The existing provenance guard holds one direction: a completion folded into `argv` breaks the anchor, because the argv carrying its completion no longer traces through the record's sentence. Nothing holds the other. Moving a genuinely prescribed token out of `argv` and into `completion` leaves the shorter argv anchoring, leaves the coverage property matching (it reads `argv_for`, which re-appends the completion), and leaves the executed command byte-identical. What inverts is the published provenance: the round reports that a record failed to prescribe a flag the record bolds in the affirmative.

**A disposition flipped off `runs`.** A form's disposition is a claim about the record, and the coverage property reads only the `runs` half. Flipping one form to `alternative` or `superseded` therefore doubles as a per-form off-switch for that property, after which a second edit can drop the token from the argv and the harness ships running a form the record warns against. Green at both steps. Measured on `arch/cycles` and on `test/isolation`, and the two behave differently: on `arch/cycles` the shortened argv comes to equal a second form the record already declares `superseded`, while on `test/isolation`, whose `runs` forms number one, the shortened argv equals no declared form at all and every property in the file stays green.

**`then` and `argv` order.** Swapping the two fails only tests that pin literal tuples, whose assertion messages read as an invitation to update the literal. Nothing property-shaped holds the order of the two commands against the record's own sentence, so once the literal is updated the swap ships with the coverage report printed before the suite that produces it.

## The four properties

All four live in `tests/scripts/test_python_fixture_harness.py`. `scripts/run_python_fixture_lens.py` takes docstring corrections only and no behaviour change. No check record needs editing.

### 1. `argv` is maximal against the quote

No token of an entry's `completion` may be matched exactly by an unmarked token of that entry's own `record_quote`. A completion token the record writes concretely is a token the record prescribed, and a table claiming otherwise falsifies the round's output.

The rule leaves the legitimate shape alone for a structural reason rather than by exception. A placeholder fill is the canonical completion: the record writes `--cov=<pkg>` and the completion supplies `--cov=fixture_app`, and those two are never equal, so the mark semantics `_matches` already carries do the work. Measured over all 13 completions, exactly one entry hits the rule.

That one is `docs/docstring-coverage` with `ruff`, whose completion is `check --select D` against a quote naming ruff's `D` rules. `D` is prescribed, and it cannot move into `argv`: the executed command is `ruff check --select D`, so expressing it would need `check --select` inserted between `ruff` and `D`, and a completion is appended rather than inserted. It becomes a named exception carrying that reason.

The rule fails safe in the direction it does not guard. A future completion token colliding with a word of its own quote's prose fails loudly and gets named or corrected; it never passes in silence.

### 2. No prescribed command is exactly a form the record warns against

For every form declared `alternative` or `superseded`, no prescribed command may equal it token for token, comparing through `_concrete` and `_matches` so that a form carrying a placeholder compares as the record wrote it. The commands read are each partition's prescribed argv and the entry's `then`. Measured across the 7 non-`runs` forms, 0 commands equal one today.

Supplied routes are excluded by construction rather than by name. A supplied route is authored in the table rather than transcribed from a record, so by construction it answers to no declaration, which is why `deps/vulnerabilities` can declare `pip-audit -r <requirements>` `superseded` truthfully while the uv partition's supplied route runs exactly that form.

Two limits, both stated on the property:

- Equality, so a non-`runs` form run as a strict prefix plus an unrelated token escapes. Containment cannot be the test: a record commonly supersedes a form by extending it, and all three of the tree's `superseded` forms are subsequences of the longer command that narrows them, so a containment rule would fire on three correct entries.
- It reads the table's declaration, not the record's prose. Which form a record warns against is not mechanically extractable, so a disposition that is simply wrong about the record remains a reading pass.

### 3. An entry declaring forms declares one it runs

This is what makes the flip fail at its first edit. An entry whose declared forms include none marked `runs` has switched the coverage property off entirely for itself, after which dropping a token from its argv is unguarded - which is exactly what the `test/isolation` measurement shows.

Two entries need naming: `deps/licenses` with `pip-licenses` and `test/determinism` with `pytest-randomly`. Each declares a single `alternative` form, truthfully - the record's only named form is one the harness deliberately does not run, and what it runs instead is the plain command the quote prescribes, which the anchor guard holds. Their residual exposure is stated with them rather than left implicit.

### 4. The second command follows the first in the record

Where an entry carries a `then`, `argv + then` must trace through the record's quote in order. Measured on the one entry that carries one: forward anchors, reversed does not, so the property both holds today and fails on the swap.

`test_a_two_step_route_keeps_its_second_command` goes with it. A literal tuple pinned in a test is the shape the issue names: it fails on the swap in a way that reads as a stale literal to update. The end-to-end assertion on the executed command stays, because it claims something the property does not - that the route actually ran its second command.

## Exceptions carry the file's existing idiom

Each of the three named exceptions above goes into a set the property asserts is *exercised*, the idiom the anchor guard's `unanchored` set already uses. An entry that stops needing its exception fails the suite rather than carrying it silently, so removing a dead exception does not depend on somebody noticing.

## Prose that becomes false

Three passages currently document these gaps as open, and each is load-bearing for a reader deciding what the suite guarantees:

- `test_folding_a_completion_into_the_argv_breaks_the_anchor`, whose docstring states that the other direction "has no guard anywhere" and instructs the reader to treat a `note` claiming a record omitted something as an unverified claim.
- `Invocation.forms` in the lens, whose docstring states that a form the harness runs while declaring it `superseded` or `alternative` passes every test in the suite, and describes the disposition as a per-form off-switch.
- `Invocation.then`, which says what the field holds and nothing about what holds its order.

Correcting them is part of the work, not follow-up. The sweep for prose the change invalidated without touching goes to a subagent that has not seen the implementation, per the repository's stale-prose rule.

## Acceptance

Each property gets a unit test built on a synthetic `Invocation` that proves it fails in the direction it guards. The tree passes all four today, so the tree cannot distinguish a live rule from a dead one - the same reason `test_every_partitions_route_is_held_against_the_quote` is built rather than asserted about the family.

Then four mutations, each run and reverted, each confirming both directions:

1. Demote `--show-dot` from `arch/cycles`'s argv into its completion. Property 1 fails.
2. Flip `test/isolation`'s only form to `alternative`. Property 3 fails.
3. Flip `arch/cycles`'s `runs` form to `alternative` and drop `--show-dot` from the argv. Properties 2 and 3 both fail.
4. Swap `test/coverage-reach`'s `argv` and `then`. Property 4 fails.

The suite is green before and after each revert, and the four mutations are the record of what the round bought.

## Out of scope

The two sibling gaps from the same round stay in their own issues. #54 is section scoping: every property here reads the source line holding `record_quote` or the paragraphs of `## Tooling fallback`, so a prescription written in a `## Fix` section is watched by nothing, and deciding whether a command there is a prescription or a remediation example is the work. #56 is the extractor: fenced blocks, unbackticked prose, and the degeneration of the placeholder mark on a short glued flag.
