# Part 5 — Evaluation: How We Decide

This is where the "evidence over intuition" throughline becomes a method. Prompt wording, context engineering, model and parameter selection, regex and filter tuning, pipeline architecture — none of these are settled by intuition or by "the tests still pass." They are settled by evidence produced against a dataset we trust. This page is the reasoning; the machinery it points to lives in the [eval docs](../eval/).

> The canonical, standalone statement of this philosophy is [Data-Driven Development — How We Decide](../eval/data-driven-development.md). This page is its handbook-facing companion: the same convictions, connected to the rest of how we work. If you read one eval doc, read that one.

## Why: the enemy is false confidence

Every non-trivial change is a hypothesis — *this will be better.* "Better" is only meaningful against a metric, and a metric is only trustworthy against a dataset the change under test did not get to define.

The failure mode is not *no* confidence. It is **false** confidence. Adding regex patterns until the suite is green, tweaking a prompt until the one example in front of you reads well, shipping the model that impressed in a demo — none of these leave you uncertain. They leave you confidently wrong, and that is worse than uncertainty, because confidence is when you stop looking. The whole discipline exists to keep a decision *falsifiable*: make the dataset and the metric exist before the decision, so a wrong turn is visible instead of comfortable.

## The loop

Build or extend a validation dataset → measure candidates against it → interpret with variance and cost → decide and ship → **re-measure after shipping**, because the change surfaces new failure forms, and those become the next dataset extension and the next hypothesis. The loop does not terminate; it is how the system stays honest as the corpus and the models drift.

## Building a dataset you can trust

The dataset is the load-bearing part. A good measurement against a bad dataset is worse than no measurement, because it launders a blind spot into a number.

**The cardinal rule: candidates must come from a source independent of the system under test.** The fastest way to fool yourself about a detector is to build its evaluation set from its own output — run it over the corpus, label what it surfaced, score against that. The gold then contains only the forms the detector already finds, recall comes out near-perfect *by construction*, and the evaluation is blind to every real miss. It looks exactly like success. This is *grading your own homework*, and it is the single easiest trap. When you must bootstrap from the system's own matches, add an independent negative sample to expose and bound the leak.

Three dataset shapes recur, matched to what an independent signal looks like:

| Shape | When it fits | How independence is achieved |
|---|---|---|
| **Expert ground truth** | The output is a rich answer whose quality a domain expert must judge (legal-research responses). | Experts curate the reference answer independently of the agent. See [ground-truth evaluation](../eval/gt-evaluation.md). |
| **Two-annotator gold** | The output is a set of discrete items (citations, key-value pairs) over a sample-able corpus. | Two annotators that *fail differently* (a regex and an LLM, never two regexes) each label; agreements auto-accept, disagreements are quarantined for a human. The disagreements are where the learning is. |
| **Anchor-based recall probe** | You need recall over a huge unlabeled corpus you cannot label fully. | Measure against an independent, higher-recall *anchor* that co-occurs with the entity and fails differently from the extractor (an authority's *name* as the anchor for its *acts*). The anchor set is the recall denominator. See [anchor-based recall](../stories/2026-07-10-anchor-based-recall-for-entity-extractors.md). |

Two more disciplines, both cheap and both routinely skipped:

- **Measure prevalence before you plan the harvest.** Knowing an entity appears in ~2% of documents changes the sampling strategy more than any accuracy gain — at that density, uniform random sampling can never accumulate enough positives per class, so you harvest from the anchor pool instead. Prevalence is cheap to estimate the moment you have any rough detector, and knowing it up front is often worth more than the headline accuracy number, because it decides whether your planned method can build a representative dataset *at all*.
- **Freeze the dataset for the duration of a comparison.** A benchmark is only comparable to itself. Changing the gold, the queries, or the thresholds mid-experiment silently invalidates every cross-run number — the results still render, they just no longer mean what they say. Extend the dataset *between* experiments, never *within* one.

## Measuring honestly

Once the dataset exists, the measurement has to be honest about three things point estimates hide:

- **Variance.** A single run of a stochastic system is an anecdote, not a result; a number without a variance is not a measurement. Run each candidate several times and report the spread. The [staged funnel](../eval/methodology.md) flags configurations whose coefficient of variation is too high to trust. Comparisons need enough runs that a real difference clears the noise band, or a swing that is pure variance reads as an improvement.
- **Full cost, not the convenient part.** Most choices are quality/cost trade-offs, so quality alone can't decide them (see [Part 4 — Observability](observability.md) on full-cost accounting). On cached-context workloads the cache read/write tokens often dominate and are invisible if you count only input/output; sub-agent calls, latency, and retries all belong in the total. Estimating cost from token counts instead of actual billing can flip a conclusion. Lead with absolute figures (a few cents per query), not percentages.
- **One variable at a time.** The before/after must be genuinely like-for-like: same documents, same queries, one rule or parameter changed. A comparison that moves two things at once measures neither.

## Which approach fits the decision

The approaches are not interchangeable; each answers a different question. Prefer the cheapest that actually answers *yours*.

| The decision you face | Approach | Doc |
|---|---|---|
| Which model / temperature / params to ship, across many candidates | **Staged evaluation funnel** — cheap deterministic gates eliminate the clearly-bad, a composite score ranks survivors, optional semantic scoring enriches | [methodology.md](../eval/methodology.md) |
| Is variant A better than variant B (a prompt change, a feature flag) | **Blind paired A/B** — human + LLM-as-judge scoring with correlation analysis | [ab-testing.md](../eval/ab-testing.md) |
| How good is a rich answer against what an expert would accept | **Ground-truth evaluation** — claim extraction, recall/coverage/consistency vs an expert baseline | [gt-evaluation.md](../eval/gt-evaluation.md) |
| Extractor *recall* over a huge unlabeled corpus | **Anchor-based recall probe** | [anchor-based recall](../stories/2026-07-10-anchor-based-recall-for-entity-extractors.md) |

The eval tier that powers all of this is described in [eval-framework architecture](../architecture/eval-framework.md); reproducible golden-set benchmarking is worked through in [extraction-quality benchmark](../architecture/extraction-quality-benchmark.md).

## LLM-as-judge vs human-in-the-loop

An LLM judge is fast, cheap, and repeatable; a human expert is the ground we actually care about but is slow and scarce. The point is not to pick one — it is to **use the cheap judge only where we've shown it agrees with the expensive one.** The A/B framework runs both and reports human/LLM *correlation*: the judge is trusted on the dimensions where it tracks the human, and the human's time is spent where it doesn't. Efficiency metrics (utilization, cost, latency, citation counts) are cheap and tempting, but two options can tie on every efficiency metric while differing in output quality, and the efficiency numbers are silent about it. Measure both: an efficiency metric for how little is wasted, and an independent quality evaluation for how good the result is.

**Ground truth is a revisable verdict, not bedrock.** A labeled dataset was produced by an earlier inquiry — people, under time pressure, with their own purpose — and inquiry is fallible. So when a model disagrees with the gold label, the default reflex to count it against the model is wrong: the disagreement is evidence about *two* inquiries. Sometimes it flags a model error; sometimes it surfaces a mislabeled example (a hand-labeled "issue date" set that recorded the print date when the operative date was the signature date cannot be fixed by fitting harder to the labels). The useful question is not "which is correct in the abstract" but "which reading leads to more reliable downstream action." That reframes evaluation from grading to *diagnosis*: a disagreement is a place to look, not just a point deducted.

## Evaluating a multi-agent system unit by unit

The legal-search agent is an orchestrator that spawns a retriever, a web-research sub-agent, and a writer. The temptation is to score the whole pipeline end-to-end. Resist it: an end-to-end metric is far noisier and often ill-defined — when a final answer is wrong you cannot tell *which* unit failed, and "is the answer good?" resists a crisp success criterion.

Because the units have well-defined interfaces, they are separately *evaluable*, and each takes its own golden dataset and its own metric. Evaluate the retriever's source inventory against a sources gold; evaluate the web sub-agent's findings on their own; evaluate the writer's report against expert ground truth. A per-unit golden dataset localizes the measurement the same way explicit units localize a failure. This is also the design principle behind the architecture — see [multi-agent decomposition](../architecture/multi-agent-decomposition.md) — and it is the eval face of the [three-layer model](three-layer-model.md), where each layer is scored on its own output instead of being hidden inside one number. The [architecture comparison](../eval/2026-05-20-architecture-comparison.md) is a worked example of measuring monolithic vs pipeline vs orchestrator designs this way.

## Escalation ladders: spend measurement where it pays

A recurring shape across these decisions: a cheap, high-precision method handles the common case, and only the *residual* escalates to a more expensive, higher-recall method. A regex fast-path settles the enumerable citation forms and hands the long tail to an LLM; a cheap-model filter feeds a capable-model verifier feeds a human adjudicator (the [filter-verify-escalate cascade](../stories/2026-07-13-filter-verify-escalate-cascade.md)); cheap deterministic gates precede expensive semantic scoring in the funnel.

The ladder is itself a data-driven decision: **you need a measurement to know where the precision/recall crossover sits** — the point at which the next missed case is better handled by escalating than by extending the cheap method. Regex is a *precision floor, not a recall guarantee*; extending it past the crossover (another pattern for a form nobody writes) costs more than it returns, and the anchor-based gold is how you measure whether escalation earned its cost.

## How you fool yourself (the anti-patterns to name out loud)

Each of these *feels* like progress, which is why it's worth naming: grading your own homework (gold built from the system under test); "we added more patterns" (a green suite proves only the cases you wrote down, and is silent on the fraction you never imagined); the single run (trusting one execution of a stochastic system); quality without cost (declaring a winner on quality alone when the decision was always a trade-off); moving the goalposts mid-experiment (adjusting thresholds/queries/gold while a comparison runs); demo-driven selection (an example is not a dataset).

## See also

- [Data-Driven Development](../eval/data-driven-development.md) — the standalone philosophy (read first)
- [Staged funnel](../eval/methodology.md) · [A/B testing](../eval/ab-testing.md) · [Ground-truth evaluation](../eval/gt-evaluation.md)
- [Eval-framework architecture](../architecture/eval-framework.md) · [Extraction-quality benchmark](../architecture/extraction-quality-benchmark.md)
- [Evaluation history](../leaderboards/evaluation-history.md) and the [leaderboards](../leaderboards/) — the results trail
- Handbook: [Part 4 — Observability](observability.md) · [Part 6 — Three-layer model](three-layer-model.md) · [Part 7 — Documentation](documentation.md)
