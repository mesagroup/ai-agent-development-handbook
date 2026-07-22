# Part 5 — Evaluation: How We Decide

This is where the "evidence over intuition" throughline becomes a method. Prompt wording, context engineering, model and parameter selection, regex and filter tuning, pipeline architecture — none of these are settled by intuition or by "the tests still pass." They are settled by evidence produced against a dataset we trust. This page is the reasoning; the concrete method you reach for depends on the shape of the decision.

## Why: the enemy is false confidence

Every non-trivial change is a hypothesis — *this will be better.* "Better" is only meaningful against a metric, and a metric is only trustworthy against a dataset the change under test did not get to define.

The failure mode is not *no* confidence. It is **false** confidence. Adding patterns until the suite is green, tweaking a prompt until the one example in front of you reads well, shipping the model that impressed in a demo — none of these leave you uncertain. They leave you confidently wrong, and that is worse than uncertainty, because confidence is when you stop looking. The whole discipline exists to keep a decision *falsifiable*: make the dataset and the metric exist before the decision, so a wrong turn is visible instead of comfortable.

## The loop

Build or extend a validation dataset → measure candidates against it → interpret with variance and cost → decide and ship → **re-measure after shipping**, because the change surfaces new failure forms, and those become the next dataset extension and the next hypothesis. The loop does not terminate; it is how the system stays honest as the data and the models drift. Record each decision and its evidence where the next person can find it ([Part 7](documentation.md)).

## Building a dataset you can trust

The dataset is the load-bearing part. A good measurement against a bad dataset is worse than no measurement, because it launders a blind spot into a number.

**The cardinal rule: candidates must come from a source independent of the system under test.** The fastest way to fool yourself about a detector is to build its evaluation set from its own output — run it over the corpus, label what it surfaced, score against that. The gold then contains only the forms the detector already finds, recall comes out near-perfect *by construction*, and the evaluation is blind to every real miss. It looks exactly like success. This is *grading your own homework*, and it is the single easiest trap. When you must bootstrap from the system's own matches, add an independent negative sample to expose and bound the leak.

Three dataset shapes recur, matched to what an independent signal looks like:

| Shape | When it fits | How independence is achieved |
|---|---|---|
| **Expert ground truth** | The output is a rich answer whose quality a domain expert must judge. | Experts curate the reference answer independently of the system. |
| **Two-annotator gold** | The output is a set of discrete items (extracted entities, key-value pairs) over a sample-able corpus. | Two annotators that *fail differently* (a rule and a model, never two rules) each label; agreements auto-accept, disagreements are quarantined for a human. The disagreements are where the learning is. |
| **Anchor-based recall probe** | You need recall over a huge unlabeled corpus you cannot label fully. | Measure against an independent, higher-recall *anchor* — a cheap signal that co-occurs with the target and fails differently from the extractor (for example, an entity's *name* as the anchor for its detailed *records*). The anchor set is the recall denominator. |

Two more disciplines, both cheap and both routinely skipped:

- **Measure prevalence before you plan the harvest.** Knowing a target appears in ~2% of items changes the sampling strategy more than any accuracy gain — at that density, uniform random sampling can never accumulate enough positives per class, so you harvest from the anchor pool instead. Prevalence is cheap to estimate the moment you have any rough detector, and knowing it up front is often worth more than the headline accuracy number, because it decides whether your planned method can build a representative dataset *at all*.
- **Freeze the dataset for the duration of a comparison.** A benchmark is only comparable to itself. Changing the gold, the queries, or the thresholds mid-experiment silently invalidates every cross-run number — the results still render, they just no longer mean what they say. Extend the dataset *between* experiments, never *within* one.

## Measuring honestly

Once the dataset exists, the measurement has to be honest about three things point estimates hide:

- **Variance.** A single run of a stochastic system is an anecdote, not a result; a number without a variance is not a measurement. Run each candidate several times and report the spread; flag configurations whose run-to-run variability is too high to trust (a coefficient-of-variation cutoff works well). Comparisons need enough runs that a real difference clears the noise band, or a swing that is pure variance reads as an improvement.
- **Full cost, not the convenient part.** Most choices are quality/cost trade-offs, so quality alone can't decide them (see [Part 4 — Observability](observability.md) on full-cost accounting). On cached-context workloads the cache read/write tokens often dominate and are invisible if you count only input/output; sub-agent calls, latency, and retries all belong in the total. Estimating cost from token counts instead of actual billing can flip a conclusion. Lead with absolute figures, not percentages.
- **One variable at a time.** The before/after must be genuinely like-for-like: same inputs, same queries, one rule or parameter changed. A comparison that moves two things at once measures neither.

## Which approach fits the decision

The approaches are not interchangeable; each answers a different question. Prefer the cheapest that actually answers *yours*.

| The decision you face | Approach |
|---|---|
| Which model / temperature / params to ship, across many candidates | **Staged evaluation funnel** — cheap deterministic gates eliminate the clearly-bad, a composite score ranks survivors, optional semantic scoring enriches. |
| Is variant A better than variant B (a prompt change, a feature flag) | **Blind paired A/B** — human + LLM-as-judge scoring with correlation analysis. |
| How good is a rich answer against what an expert would accept | **Ground-truth evaluation** — claim extraction, recall/coverage/consistency vs an expert baseline. |
| An extractor's *recall* over a huge unlabeled corpus | **Anchor-based recall probe** — score against an independent higher-recall anchor. |
| Which of several implementations renders best against a fixed target | **Reproducible golden-set benchmark** — a metric suite over a frozen golden set. |

The funnel exists precisely so you spend expensive semantic evaluation only on candidates that already cleared the cheap gates.

## LLM-as-judge vs human-in-the-loop

An LLM judge is fast, cheap, and repeatable; a human expert is the ground we actually care about but is slow and scarce. The point is not to pick one — it is to **use the cheap judge only where you've shown it agrees with the expensive one.** Run both on a sample and report human/LLM *correlation*: trust the judge on the dimensions where it tracks the human, and spend the human's time where it doesn't. Efficiency metrics (utilization, cost, latency) are cheap and tempting, but two options can tie on every efficiency metric while differing in output quality, and the efficiency numbers are silent about it. Measure both: an efficiency metric for how little is wasted, and an independent quality evaluation for how good the result is.

**Ground truth is a revisable verdict, not bedrock.** A labeled dataset was produced by an earlier inquiry — people, under time pressure, with their own purpose — and inquiry is fallible. So when a model disagrees with the gold label, the default reflex to count it against the model is wrong: the disagreement is evidence about *two* inquiries. Sometimes it flags a model error; sometimes it surfaces a mislabeled example (a hand-labeled "issue date" that recorded the print date when the operative date was the signature date cannot be fixed by fitting harder to the labels). The useful question is not "which is correct in the abstract" but "which reading leads to more reliable downstream action." That reframes evaluation from grading to *diagnosis*: a disagreement is a place to look, not just a point deducted.

## Evaluating a multi-agent system unit by unit

A multi-agent system — say an orchestrator that spawns a retriever, a tool-using sub-agent, and a writer — invites scoring the whole pipeline end-to-end. Resist it: an end-to-end metric is far noisier and often ill-defined — when the final answer is wrong you cannot tell *which* unit failed, and "is the answer good?" resists a crisp success criterion.

Because the units have well-defined interfaces, they are separately *evaluable*, and each takes its own golden dataset and its own metric. Evaluate the retriever's output against a retrieval gold; evaluate the tool-using sub-agent's findings on their own; evaluate the writer's report against expert ground truth. A per-unit golden dataset localizes the measurement the same way explicit units localize a failure. This is the eval face of the [three-layer model](three-layer-model.md), where each layer is scored on its own output instead of being hidden inside one number — and it is why the [architecture](codebase-structure.md) exposes the units as separately-runnable pieces in the first place.

## Escalation ladders: spend measurement where it pays

A recurring shape across these decisions: a cheap, high-precision method handles the common case, and only the *residual* escalates to a more expensive, higher-recall method. A rule-based fast-path settles the enumerable cases and hands the long tail to a model; a cheap-model filter feeds a capable-model verifier feeds a human adjudicator; cheap deterministic gates precede expensive semantic scoring.

The ladder is itself a data-driven decision: **you need a measurement to know where the precision/recall crossover sits** — the point at which the next missed case is better handled by escalating than by extending the cheap method. A rule set is a *precision floor, not a recall guarantee*; extending it past the crossover (another pattern for a form nobody writes) costs more than it returns, and an independent recall probe is how you measure whether escalation earned its cost.

## How you fool yourself (the anti-patterns to name out loud)

Each of these *feels* like progress, which is why it's worth naming: grading your own homework (gold built from the system under test); "we added more patterns" (a green suite proves only the cases you wrote down, and is silent on the fraction you never imagined); the single run (trusting one execution of a stochastic system); quality without cost (declaring a winner on quality alone when the decision was always a trade-off); moving the goalposts mid-experiment (adjusting thresholds/queries/gold while a comparison runs); demo-driven selection (an example is not a dataset).

## See also

- [Part 4 — Observability](observability.md) — instrument before you tune; pair efficiency with quality.
- [Part 6 — Three-layer model](three-layer-model.md) — separately-evaluable layers.
- [Part 7 — Documentation](documentation.md) — recording the results trail.
- [Handbook index](README.md).
