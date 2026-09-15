# Handbook: Bounding and SOP Coverage Gaps — Design

**Issue:** `<origin-repo>#538`
**Date:** 2026-07-28
**Status:** approved in session (breaker placement and execution approach both confirmed by the user)

## Goal

Close the four coverage gaps found while writing the troubleshooting guide (`<origin-repo>#536`): four mechanisms the guide routes readers to, where the target section owns the topic but never names the mechanism. Three of the four are production footguns an agent-engineering handbook should name outright (an agent loop with no cycle budget, an unbounded tool output, an SOP with no stop condition); the fourth (the circuit breaker) is the standard answer to a degraded dependency, which Part 5 gestures at without naming. A fifth, adjacent point rides along: bounded retries want an idempotency caveat.

## Root cause of the gap

Part 5's "Make bounding the default" bounds exactly one dimension. All three of its bullets bound **time** (wall-clock and idle timeouts, connect and read timeouts, time-bound teardown), and its closing line generalizes as "an unbounded external call is a latent production hang". That framing is what let the other two dimensions fall out: the agent loop's own **cycles**, and the **size** of what a tool hands back. Widening the section means widening its framing, not only appending bullets.

## Decisions

- **Circuit breaker goes in "Make bounding the default"**, as a bullet alongside the others, and the guide's route for it moves from "Build the harness, don't inline the plumbing" to the bounding section. Rationale: a breaker bounds how many times you keep calling a failing dependency, so it is the same kind of rule as the rest of the list; and the plumbing section is an argument about *where* reliability decisions live, not an inventory of mechanisms. Keeping every concrete reliability default in one list is also what makes the section findable from a symptom.
- **Idempotency attaches to the existing hardened-HTTP-client bullet**, which is where `bounded retries` is already prescribed. It is a caveat on a rule the handbook already gives, not a rule of its own.
- **The SOP stop condition goes in Part 2's SOP-shape paragraph**, next to Overview / Parameters / Steps / Constraints, because it is part of what the procedure must specify rather than a separate discipline.
- **Execution: spec plus inline implementation**, no plan file and no subagent-driven development. `<origin-repo>#536` earned full SDD (a new page, fifteen entries, forty-four routes); this is one coherent editing pass over three files.

## Changes

### `docs/engineering/agent-harness.md` (Part 5)

- **"Make bounding the default"**, three new bullets: a cycle/budget bound on the agent loop; a size bound on what a tool returns (truncate, summarize, or spill to an artifact fetched on demand); a circuit breaker that trips after repeated failures and fails fast during a cooldown.
- **Hardened HTTP client bullet**: add the idempotency caveat on retries.
- **Closing paragraph**: widen "an unbounded external call is a latent production hang" so it covers the loop and the payload, not only the outbound call.
- **Checklist**: split the single bounding item into a time bound (including the retry caveat) and a loop-and-payload bound.

### `docs/engineering/implementation-disciplines.md` (Part 2)

- **"Prompt and SOP engineering"**: after the SOP-shape sentence, name the completion criterion as part of what an SOP specifies, including the early-exit conditions, so the failure exit is as explicit as the success one.

### `docs/engineering/troubleshooting.md`

- Drop the two "extending its rule to…" signposts (the cycle-bound route and the output-size route), which exist only because the target section did not name the mechanism. This also clears the cosmetic repetition parked at `<origin-repo>#536`'s merge (`bounding … bounding rule`), which sat in one of those clauses.
- Re-point the circuit-breaker route from the plumbing section to the bounding section.
- Enrich the SOP stop-condition route to name what Part 2 now says.

## Constraints

All standing `docs/engineering/` gates, binding:

- Zero em-dashes (the render script counts them; must stay 0).
- No comma splices in new prose.
- One paragraph per source line (no hard-wrap).
- Cross-links are relative `.md` links with no `#anchor` fragments; target sections in other parts are named in prose next to the part link.
- Handbook register: portable "how to" voice, no institutional "we"; clipped-imperative body; every new rule carries its *why* inline, since that is the convention the surrounding bullets keep.

**Verification gates (all four must pass):**

1. `uv run scripts/render_handbook_artifact.py --out <scratch>/handbook-check.html` (counters: em-dashes 0, residual .md hrefs 0).
2. `uv run python scripts/check_docs.py`.
3. `uv run mkdocs build --strict`.
4. `uv run python scripts/check_site_links.py site`.

## Out of scope

- **No new fix content in the guide.** The guide diagnoses and routes; the parts carry the fixes. The idempotency caveat in particular stays out of it.
- **No new entries in the guide.** The routes that exist are the ones that change.
- **No code changes**, so no new unit tests: this branch touches three Markdown files under `docs/engineering/` plus this spec.
