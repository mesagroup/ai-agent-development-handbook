---
id: eval/merge-coverage-assertion
domain: eval
locality: global
handbook:
  - lifecycle/fan-work-out-to-parallel-agents-and-merge-it-honestly-b
---

# Coverage assertion over a merged multi-agent artifact

Where the project fans work out across agents and merges what comes back, does a mechanical assertion run between the merge and the first thing that reads the merged artifact? The assertion the claim asks for is exactly one verdict per unit: the distinct count matching the expected count, no unit missing and none judged twice. The failure this catches is the one that presents as success. A merged artifact looks complete whether or not every unit reached it, so a slice that was judged twice or never leaves no error behind, and every number computed downstream is computed over it.

Two things make this repository-visible where the rest of its handbook section is not. The assertion is code that either exists at the merge site or does not, and the expected count is a number the fan-out already knows, because something decided how many units to send out. A pipeline that cannot state its expected count has the same defect in a different place, and that is this check's finding too.

**What the claim asks beyond the count.** Conflicts and gaps go to a single cleanup pass rather than being resolved inline, one at a time, by whichever agent noticed. Read what the merge site does with what the assertion finds: a pipeline that asserts and then repairs each disagreement where it falls is partitioning the cleanup the same way it partitioned the work, which is what the claim's second half forbids.

**`not-applicable` where the project runs no fan-out at all**, with what was read recorded beside it. A single-agent pipeline has no merged artifact and this check has no subject, which is not a pass. What has to be empty is the whole surface rather than the first place looked in: a project's fan-out may live in an eval runner, a batch script, a notebook, a CI matrix that shards a corpus, or an agent orchestrator, and finding none in the eval runner alone settles nothing.

## Severity

**Critical** - a merged artifact with no assertion of any kind, whose numbers are already reported or shipped. The figures downstream have no known relationship to the corpus they claim to cover.

**Important** - an assertion that counts rows but does not establish that each unit appears exactly once, so duplicates and gaps that cancel out in the total pass it.

**Important** - an expected count the pipeline cannot state, so the assertion has nothing to compare against and reduces to "the merge produced something".

**Minor** - an assertion that runs after the first consumer rather than before it, where the consumer is a report rather than a decision. The ordering is the claim, and a report regenerated from a corrected artifact costs little; a decision taken on the uncorrected one cannot be withdrawn.

## Tooling fallback

Needs reading - no tool in this domain's evidence pass reaches this. Find the fan-out sites first, then read each merge: a loop or task group that dispatches per-unit work, a `map` over a corpus whose results are concatenated, a CI job with a shard or matrix axis, a judging pipeline that slices its dataset, an agent orchestrator that collects sub-agent output. At each one, read what runs between the merge and the first consumer, and record the `file:line` of the assertion, or of the merge that has none.

**The evidence is the assertion or its absence**, never the partition's shape. Whether the project sliced its corpus sensibly is not this check's question, for the same reason `arch/import-rule-declaration` does not rate the tiers it finds declared. The finding is the missing guarantee, and a project whose slices are uneven but whose merge is asserted passes this check.

**The boundary against `eval/coverage`.** That check asks whether the behaviors that matter have evals at all, over the whole capability set. This one asks whether a merged artifact accounts for every unit that was sent out, and it is indifferent to whether those units were the right ones to send. A project can cover every behavior that matters and still merge a judging run that lost a slice; it can also assert its merges perfectly over a corpus that exercises nothing important. Report a gap under the check that owns the question rather than under both.

## Fix

**Put the assertion between the merge and the first consumer**, comparing the distinct unit count against the expected count the fan-out already holds, and failing loudly rather than warning. A warning on a path nobody reads is the same as no assertion, because the artifact travels either way.

**Route conflicts and gaps to one cleanup pass** rather than repairing them at the merge site. The units the assertion flags were produced under whatever the run knew at the time, and deciding them together is what keeps one ruling from contradicting another made an hour earlier.

**Where the expected count cannot be stated**, that is the first fix and the assertion is the second. A fan-out that does not know how many units it dispatched has no way to discover that it lost one.

## Review lens

**Assertion placement** - does the assertion run before the first consumer reads the artifact, or after it? (Highest-value catch: an assertion in a reporting step that runs at the end of the pipeline, downstream of the decision the artifact was merged to inform.)

**Count identity** - is the assertion comparing distinct units against an expected count, or comparing a row total against itself? A length check on the merged artifact passes over one duplicate and one gap, which is the exact shape this claim exists to catch.
