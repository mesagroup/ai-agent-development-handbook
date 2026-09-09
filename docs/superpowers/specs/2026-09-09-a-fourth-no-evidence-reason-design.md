# A fourth `no-evidence` reason, and the two vocabularies it has to keep in step

Issue #74. `no-evidence` carries one of three reasons, and none of them is true where a record prescribes no command for a partition: the tool is obtainable, nothing was refused, nothing failed. What is missing is the input.

**Status.** Written and self-approved under autonomous mode, with no maintainer review gate. Every decision below records the alternative it rejected and how it was settled, so any one of them can be reopened on evidence rather than on recollection. The gate that was not granted is the review of the resulting PR.

## The decision was already taken, and it is a reason rather than a status

The nightshift ledger, issue #78, records the maintainer's ruling under `## Decisions already taken`: a **fourth reason**, not a re-use of an existing one and not a prose rule, with the same "what would answer this next time" gloss the other three carry, and the suggested name `not-prescribed`. A tick may choose a better name and must record why.

The name survives. Read beside `not-permitted`, `tool-unavailable` and `tool-failed`, it reads without any knowledge of the record schema - "the record does not say to do anything here" is exactly the fact - and that is the register the other three are in. `no-route` was the alternative and it fails that test: a report reader does not know what a route is.

#74 also asks whether `audit-core`'s closed-scale argument reaches this. It does not. That argument is about the **status** scale, and its reason is specific: a fourth status would collapse the distinction between `no-evidence` and `not-applicable`. The reason vocabulary is closed under a different criterion, which this change writes down rather than leaving to be re-derived: **a reason is admissible exactly when it names a genuinely different answer to "what would answer this next time".** This case has one no other reason states - nothing about this run or this environment ever will.

`not-applicable` is not the answer instead, for the reason #74 gives and this spec verified: `not-applicable` means the check has no lens in the partition's languages, and here the record offers one and the partition speaks the language. `test/mutation`'s note already refuses `not-applicable` for a missing runner plugin on the same grounds.

## The precedence rule is the load-bearing half, and the first reading of it was wrong

The first draft of this ruling said `not-prescribed` reports wherever the record *prescribes* nothing for a partition, counting a `disposition: alternative` route as not prescribed. That is wrong, and it is wrong in the exact direction #74 names as the failure to avoid: a standing false lead.

Computed over every route in the tree, the shape #74 describes - a `kind: command` route with no shared `argv` and a per-partition map that does not name every partition - has two instances:

| record | route's tool | partitions left unnamed | sibling routes for the same language |
|---|---|---|---|
| `deps/inventory` | `cyclonedx-py` | `pylock` | `cyclonedx-py environment`, `alternative`, `resolved-tree` |
| `deps/vulnerabilities` | `pip-audit` | `uv`, `poetry`, `pipenv` | `pip-audit -r <requirements>` `superseded`; `safety`, `runs`, `resolved-tree` |

**Both records keep a route for the same language that a grant would enable.** On those partitions the honest reason is `not-permitted`: re-running with `resolved-tree` genuinely answers the check, and `deps/inventory`'s own note calls the environment route "the more accurate of the two where a tree is available". A reader told `not-prescribed` there stops; a reader told `not-permitted` gets the grant and gets an SBOM.

So the rule is **the actionable reason wins**, and the gloss carries the clause rather than leaving it to a later paragraph: `not-prescribed` reports only where the record prescribes no command for this partition *and* offers no route a grant would enable. It is stated in the sentence that decides - the route-reading instruction that tells an agent what an unnamed partition means - and not only in the vocabulary, because a rule stated where the command is chosen is the one an agent actually reads.

## Under that rule the reason has no instance in this tree, which is recorded rather than hidden

#74 says the fourth way "now has instances". The *shape* has two; the *reason*, under the purpose that justifies it, has none today, because the issue looked at the partial-map route rather than at the check's whole route set. That correction is posted on #74.

It is still worth adding, for a reason that does not depend on a current instance. `audit/SKILL.md`'s route-reading instruction already tells an agent to report `no-evidence` for exactly this case, so a status with no correct reason is reachable from an instruction that exists on `main` today. The loader admits the shape that produces it - it was widened deliberately so a record could say "these partitions have this command and the rest have none" - and a record whose only route for a language is a partial-map one is one edit away. What would be wrong is to claim an instance, which is why the count is stated as zero.

## The vocabulary lives in code too, and the two copies answer this case differently

#74's acceptance criteria name `audit-core/SKILL.md`, `audit/SKILL.md`, one check record and the obligations ledger. They do not name `scripts/run_python_fixture_lens.py`, which carries `REASONS = ("not-permitted", "tool-unavailable", "tool-failed")` and a comment justifying it: *"`audit-core` introduces the reasons as 'the three ways a check can fail to run', so a fourth reason is a value the pass that grades this file has no row for."* `tests/scripts/test_python_fixture_harness.py` pins the tuple by literal equality on the same argument. Adding a fourth reason to prose alone leaves that comment false and that docstring resting on a fact that changed, and no gate in this repository would see it.

The same comment also says how the harness already handles this case: *"a row for a record that prescribes no command carries `status: \"\"` - not a fourth status but the absence of one, because nothing ran to have a status."* A test asserts it, including that such a row's reason is none of `REASONS` and that its `why` says "prescribes no command".

**That is reconcilable, and the reconciliation is the ruling.** A harness row is one invocation's observation; the engine's matrix row is a check's verdict on a partition. Where the record prescribes no command there was no invocation, so the harness has nothing to observe and says so with an empty status. The engine still owes the reader a verdict, and that verdict is what needs the fourth reason. So:

- `audit-core` grows to four reasons.
- The lens keeps three, because it cannot produce the fourth: it never classifies a check, only what a command did. Its comment says that, instead of resting on a count of the engine's reasons that has changed.
- The pin stays a pin. Its justification is rewritten: a vocabulary is pinned so that a fourth member arrives visibly, which is a reason to pin that survives the engine growing one.

Rejected: growing `REASONS` to four to keep the mirror literal. It would add a member the lens can never emit, which weakens the assertion that reads every row against the scale, and it would leave the `status: ""` representation looking like an oversight rather than the deliberate choice its own comment records.

## Criterion 4 rests on a premise that does not hold

It asks whether `deps-audit/checks/vulnerabilities.md`'s `evidence:` block can stop asking the auditor to carry the distinction by hand. The block names two cases, "a retired endpoint and a missing scanner", and those are `tool-failed` and `tool-unavailable` - both in the vocabulary before this change. The block was working around not *using* the three reasons rather than around the missing fourth.

So it is corrected, which is what the criterion wants, for a reason the criterion misidentified: it now names the reasons the vocabulary already has instead of asking for a distinction to be supplied in prose. The record keeps the judgement that belongs to it - which case a retired advisory endpoint is - and stops asking for a taxonomy the engine owns.

## What changes

- **`audit-core/SKILL.md` step 2**: the reason list gains `not-prescribed` with its gloss and the precedence clause, the framing stops saying "three ways", and the vocabulary's growth rule is stated so the next reason is judged rather than argued from a count. The *status* scale's closed argument is untouched and is now explicitly about statuses.
- **`audit/SKILL.md`**: the `no-evidence` rendering list names the fourth reason; the route-reading sentence about an unnamed partition names it too, with the precedence clause, since that is the sentence that decides.
- **`deps-audit/checks/vulnerabilities.md`**: the `evidence:` block points at the vocabulary.
- **`scripts/run_python_fixture_lens.py`** and **`tests/scripts/test_python_fixture_harness.py`**: the comment and the pin's docstring say why the lens's three are three, without resting on the engine's count.
- **`docs/audit/sweep-obligations.md`**: the row anchored on `carries a reason, because the three ways a check can fail to run` gets a full new anchor, since that sentence changes and its test forbids trimming an anchor to whatever survived. New rows for the obligations the change adds.
- **A new guard** that the reason names in `audit-core` and in `audit/SKILL.md` are the same set, and that the lens's `REASONS` is that set minus the one it cannot produce. Three copies of one vocabulary in two languages is exactly the consistency property CLAUDE.md says to move into the validator.

## This branch conflicts with both open PRs

Cut from `main`; based on neither. Merge order stays #80, #81, then this.

- **`audit/SKILL.md`'s rendering list** is in line 52, which **#80** edits. Both edits are additive to different sentences of the same paragraph; the merged line keeps #80's runner rule and this change's fourth reason.
- **`audit/SKILL.md`'s route-reading sentence** is in line 53, which **#81** deletes, having relocated the contract into `audit-core`'s `## Running a route`. The resolution is to take #81's deletion and apply this change's sentence to the relocated copy, where the unnamed-partition rule now lives.
- **`docs/audit/sweep-obligations.md`**: three branches now edit rows of one table. This one rewrites the row whose anchor its own `audit-core` edit breaks; #80 and #81 rewrite others.

## Verification

The four gates, `tests/test_sweep_obligations.py` read rather than merely run, the new guard, and the reading pass over `audit-core` that the ledger's header asks for. Then a stale-prose pass by an agent that has not seen the change, scoped by the sentences that carry a decision: everywhere a reason name appears, and everywhere prose counts the reasons.
