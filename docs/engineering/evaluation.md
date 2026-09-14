# Part 7. Evaluation: How to Decide

*Everything so far was preparation for one question: did the change actually make the product better? Green tests cannot answer it, and neither can a demo that went well. This part answers it with evidence: a dataset fixed before the decision, a metric you can trust, and the honesty disciplines that keep both. The story's loop closes here, because what the measurement teaches becomes the next issue.*

This is where the "evidence over intuition" throughline becomes a method. Don't settle prompt wording, context engineering, model and parameter selection, regex and filter tuning, or pipeline architecture by intuition or by "the tests still pass." Settle them with evidence produced against a dataset you trust. This page is the reasoning; the concrete method you reach for depends on the shape of the decision.

## The enemy is false confidence

Treat every non-trivial change as a hypothesis, *this will be better.* "Better" is only meaningful against a metric, and a metric is only trustworthy against a dataset the change under test did not get to define.

Guard against **false** confidence, not the absence of it. Adding patterns until the suite is green, tweaking a prompt until the one example in front of you reads well, shipping the model that impressed in a demo, none of these leave you uncertain. They leave you confidently wrong, and that is worse than uncertainty, because confidence is when you stop looking. Keep every decision *falsifiable*: make the dataset and the metric exist before the decision, so a wrong turn is visible instead of comfortable.

## Run the loop

Build or extend a validation dataset → measure candidates against it → interpret with variance and cost → decide and ship → **re-measure after shipping**, because the change surfaces new failure forms, and those become the next dataset extension and the next hypothesis. Don't expect the loop to terminate; it is how the system stays honest as the data and the models drift. Record each decision and its evidence where the next person can find it ([Part 8](documentation.md)).

## Measure the behaviors that matter

Ask *whether at all* before *how well.* An eval is a measuring instrument, and the first question about any instrument is what it is pointed at. So enumerate the behaviors the product actually depends on (accuracy, grounding and citation, format adherence, refusal handling, latency and cost, and the specific *failure modes* that would hurt in production) and map each to an eval that exercises it. **Treat an unevaluated capability as an unmonitored one:** the ones with no test case are exactly where a regression ships silently, and a capability that has a leaderboard entry but no case for its key failure mode is still a gap. This is the behavioural twin of test coverage ([Part 2](implementation-disciplines.md)), same idea, one level up from code to conduct. Include the adversarial modes: does the agent hold up when untrusted or tool-returned content tries to redirect it? Make that behavioural injection-resistance an eval dimension; the security-surface counterpart is in [Part 9](security-supply-chain.md). Match the *grader* to the behavior too: some checks are **code-graded** (a deterministic assertion on the output: exact match, schema validity, a required citation present), some are **judge-graded** (an LLM rubric, but only where it has been calibrated against a human, below), and some are **trajectory-graded** (an assertion on the *path* the run took, for example that a forbidden tool was never called or that retrieval ran before generation). The trajectory grader is the only one that sees *how* the agent reached its answer rather than only whether the answer was right, which is what you need for behaviours the final output does not reveal.

## Build a dataset you can trust

The dataset is the load-bearing part. A good measurement against a bad dataset is worse than no measurement, because it launders a blind spot into a number.

**Follow the cardinal rule: draw candidates from a source independent of the system under test.** The fastest way to fool yourself about a detector is to build its evaluation set from its own output, run it over the corpus, label what it surfaced, score against that. The gold then contains only the forms the detector already finds, recall comes out near-perfect *by construction*, and the evaluation is blind to every real miss. It looks exactly like success. This is *grading your own homework*, and it is the single easiest trap. When you must bootstrap from the system's own matches, add an independent negative sample to expose and bound the leak.

Pick the dataset shape that matches what an independent signal looks like:

| Shape | When it fits | How independence is achieved |
|---|---|---|
| **Expert ground truth** | The output is a rich answer whose quality a domain expert must judge. | Experts curate the reference answer independently of the system. |
| **Two-annotator gold** | The output is a set of discrete items (extracted entities, key-value pairs) over a sample-able corpus. | Two annotators that *fail differently* (a rule and a model, never two rules) each label; agreements auto-accept, disagreements are quarantined for a human. The disagreements are where the learning is. |
| **Anchor-based recall probe** | You need recall over a huge unlabeled corpus you cannot label fully. | Measure against an independent, higher-recall *anchor*, a cheap signal that co-occurs with the target and fails differently from the extractor (for example, an entity's *name* as the anchor for its detailed *records*). The anchor set is the recall denominator. |

Two more disciplines, both cheap and both routinely skipped:

- **Measure prevalence before you plan the harvest.** Knowing a target appears in ~2% of items changes the sampling strategy more than any accuracy gain, at that density, uniform random sampling can never accumulate enough positives per class, so harvest from the anchor pool instead. Prevalence is cheap to estimate the moment you have any rough detector, and knowing it up front is often worth more than the headline accuracy number, because it decides whether your planned method can build a representative dataset *at all*.
- **Freeze the dataset for the duration of a comparison.** A benchmark is only comparable to itself. Changing the gold, the queries, or the thresholds mid-experiment silently invalidates every cross-run number, the results still render, they just no longer mean what they say. Extend the dataset *between* experiments, never *within* one.

## Measure honestly

Once the dataset exists, be honest about the things point estimates hide:

- **Report variance.** A single run of a stochastic system is an anecdote, not a result; a number without a variance is not a measurement. Run each candidate several times and report the spread; flag configurations whose run-to-run variability is too high to trust (a coefficient-of-variation cutoff works well). Give comparisons enough runs that a real difference clears the noise band, or a swing that is pure variance reads as an improvement. For pass/fail cases rather than scalar scores, report the same honesty a different way: run each case N times and record its reliability band (how many of N passed), because *k of N* separates a case that is flaky from one that is genuinely failing, which a single pass/fail hides. Alongside the per-case bands, report the strict **pass^N** aggregate (the probability that all N runs pass), the honest answer to "will this work every time" that an average of lucky runs flatters. How high that reliability bar must sit is a business decision tied to the change's criticality ([Part 1](lifecycle.md)): a commodity path tolerates a band a core differentiator cannot.
- **Account for full cost, not the convenient part.** Most choices are quality/cost trade-offs, so quality alone can't decide them (see [Part 6. Observability](observability.md) on full-cost accounting). On cached-context workloads the cache read/write tokens often dominate and are invisible if you count only input/output; put sub-agent calls, latency, and retries in the total. Take cost from actual billing, not token counts, estimating can flip a conclusion. Lead with absolute figures, not percentages.
- **Change one variable at a time.** Keep the before/after genuinely like-for-like: same inputs, same queries, one rule or parameter changed. A comparison that moves two things at once measures neither.
- **Separate failure types.** A refusal or an API error is not a quality failure, and folding them together corrupts the score, don't penalize a model for a sub-agent's refusal or a transient timeout. Bucket them apart so a low score means "answered badly," not "didn't answer."
- **Make it reproducible.** A headline number is only trustworthy if you can regenerate it: pin the model version, record the full config (model, params, dataset revision, seed where feasible), and keep the run's artifacts. A pinned model matters as much as a pinned dependency ([Part 9](security-supply-chain.md)), a silent provider upgrade moves your numbers out from under you, and an unacknowledged non-determinism turns a "regression" into noise.

## Pick the approach that fits the decision

The approaches are not interchangeable; each answers a different question. Reach for the cheapest that actually answers *yours*.

| The decision you face | Approach |
|---|---|
| Which model / temperature / params to ship, across many candidates | **Staged evaluation funnel**: cheap deterministic gates eliminate the clearly-bad, a composite score ranks survivors, optional semantic scoring enriches. |
| Is variant A better than variant B (a prompt change, a feature flag) | **Blind paired A/B**: human + [LLM-as-judge](https://arxiv.org/abs/2306.05685) scoring with correlation analysis. |
| How good is a rich answer against what an expert would accept | **Ground-truth evaluation**: claim extraction, recall/coverage/consistency vs an expert baseline. |
| An extractor's *recall* over a huge unlabeled corpus | **Anchor-based recall probe**: score against an independent higher-recall anchor. |
| Which of several implementations renders best against a fixed target | **Reproducible golden-set benchmark**: a metric suite over a frozen golden set. |

The funnel exists precisely so you spend expensive semantic evaluation only on candidates that already cleared the cheap gates.

```funnel title="The staged screening funnel, log scale; counts illustrative"
Many candidates              10000
Cheap deterministic gates     2000
Composite score                400
Semantic scoring, LLM judge     60
Human adjudication               8
The one you ship                 1
```

## Grow the eval into a gate

An eval does not start life as a merge blocker; it earns that authority in stages. First run it **offline** against a fixed dataset, to answer a question you are asking deliberately. Once it is stable, run it in **shadow mode**: score real production traffic and log the result, but let nothing block on it, so you learn what the metric does on live inputs (and where it is noisy) before it can stop a merge. Only after it has proven trustworthy in shadow does it become a **merge-blocking CI gate**. Promote an eval past a rung it has not earned and you gate on noise, which teaches the team to ignore the gate, which is worse than having none.

At every rung the loop still feeds itself: a miss the eval let through in production becomes a new case in the dataset, so the gate that let it slip cannot let the same class slip twice. That is the same feedback loop this part opened with, now wired into the pipeline.

## Use the LLM judge only where it agrees with the human

An LLM judge is fast, cheap, and repeatable; a human expert is the ground you actually care about but is slow and scarce. Don't pick one, **use the cheap judge only where you've shown it agrees with the expensive one.** Run both on a sample and report human/LLM *correlation*: trust the judge on the dimensions where it tracks the human, and spend the human's time where it doesn't. Efficiency metrics (utilization, cost, latency) are cheap and tempting, but two options can tie on every efficiency metric while differing in output quality, and the efficiency numbers are silent about it. Measure both: an efficiency metric for how little is wasted, and an independent quality evaluation for how good the result is.

**Treat ground truth as a revisable verdict, not bedrock.** A labeled dataset was produced by an earlier inquiry, people, under time pressure, with their own purpose, and inquiry is fallible. So when a model disagrees with the gold label, resist the default reflex to count it against the model: the disagreement is evidence about *two* inquiries. Sometimes it flags a model error; sometimes it surfaces a mislabeled example (a hand-labeled "issue date" that recorded the print date when the operative date was the signature date cannot be fixed by fitting harder to the labels). Ask not "which is correct in the abstract" but "which reading leads to more reliable downstream action." That reframes evaluation from grading to *diagnosis*: a disagreement is a place to look, not just a point deducted.

## Agreement is not corroboration

Running one input past several agents and counting how many agree is not several measurements. They inherit that input's errors together: where the artifact under review is wrong or merely convincing, every reader of it is wrong the same way, and their agreement measures the artifact rather than the thing it describes. It has happened in review - more than one reviewer reporting a concurrency defect as fixed, each of them reading a docstring that claimed a re-read the code did not perform, until the reviewer that executed the code found it. What buys independence is diversity of *method*, not redundancy of reader: one that executes, one that reads, one that tests, is worth more than any number of readers of a single kind. So treat consensus among same-method readers as one reading whose error bars you cannot see, and where a judgment matters, spend the next unit of budget on a different method rather than another reader.

## Ask for a described category, not a bare number

Where the model itself must return a judgment - a confidence, a quality verdict, a severity - ask for a point on a **small closed scale whose every point carries a described trigger**, and keep free numbers for quantities something other than the model computed. Low / Medium / High, each with a sentence saying when it applies, beats "your confidence from 0.0 to 1.0"; four described star ratings beat a float. The description is the load-bearing part: a label with no stated trigger is only a coarser number.

The first reason is that the float's resolution is fiction. Verbalized confidence is heavily discretized: a model does not sweep the range it is offered but lands on a few round anchors, and [the three most common values account for more than 78% of responses in every model tested](https://arxiv.org/abs/2603.09309). A 0-100 field advertises a hundred and one distinct verdicts for a signal that moves in about three, and everything downstream reads that precision as real. Fewness measurably helps: the same study finds every model reaching significantly higher metacognitive efficiency on a 0-20 scale than on 0-100, and finds that truncating the range from below only drives responses harder against the ceiling instead of spreading them into the room that is left. It tested numeric scales alone, so it argues for a short scale rather than for labels; the case for describing each point is separate, and follows.

The second is that a bare number invites a threshold nobody argued for. "Act on Moderate and above" is a policy someone had to defend; `>= 0.62` is a number someone nudged until the output looked right, and a cutoff placed between two rubric anchors asks graders for a distinction the rubric never defined. Named boundaries also give raters a shared referent, so two graders, or one grader twice, land in the same bucket, where `0.7` means whatever each run took it to mean. That reproducibility is what makes the agreement above concretely measurable: an ordinal scale is scored with a rank-aware statistic such as quadratic weighted kappa rather than with an unspecified correlation.

Be clear about what this rule is not, because the tempting reason for it is the wrong one and the evidence runs against it. Asked directly, an RLHF-tuned model's [stated confidence is often better calibrated than its own token probabilities](https://arxiv.org/abs/2305.14975), and that same study sets numeric probabilities against a described set of linguistic likelihood expressions and concludes the model does at least as well with numbers as with words. So this is not a calibration claim, and nothing here says a label reads truer than a figure: a short numeric scale with described points satisfies the rule exactly as a worded one does. What it rejects is the *bare* number - unanchored and over-resolved - because the interface is the thing at stake: what a scale advertises it can resolve, whether two raters can land on the same point, and how much weight a cutoff on it can honestly bear.

## Evaluate a multi-agent system unit by unit

A multi-agent system, say an orchestrator that spawns a retriever, a tool-using sub-agent, and a writer, invites scoring the whole pipeline end-to-end. Resist it: an end-to-end metric is far noisier and often ill-defined, when the final answer is wrong you cannot tell *which* unit failed, and "is the answer good?" resists a crisp success criterion.

Because the units have well-defined interfaces, evaluate them separately, each takes its own golden dataset and its own metric. Score the retriever's output against a retrieval gold; score the tool-using sub-agent's findings on their own; score the writer's report against expert ground truth. A per-unit golden dataset localizes the measurement the same way explicit units localize a failure. This is the eval face of the [three-layer model](three-layer-model.md), where each layer is scored on its own output instead of being hidden inside one number, and it is why the [architecture](codebase-structure.md) exposes the units as separately-runnable pieces in the first place.

## Build escalation ladders: spend measurement where it pays

A recurring shape across these decisions: let a cheap, high-precision method handle the common case, and escalate only the *residual* to a more expensive, higher-recall method. A rule-based fast-path settles the enumerable cases and hands the long tail to a model; a cheap-model filter feeds a capable-model verifier feeds a human adjudicator; cheap deterministic gates precede expensive semantic scoring. Because each stage settles most of what reaches it, the most expensive method sees the least traffic - the same taper the staged screening funnel above draws, over a different population: there it is candidates eliminated in a one-off selection, here it is cases settled in a continuous stream.

The ladder is itself a data-driven decision: **you need a measurement to know where the precision/recall crossover sits**: the point at which the next missed case is better handled by escalating than by extending the cheap method. A rule set is a *precision floor, not a recall guarantee*; extending it past the crossover (another pattern for a form nobody writes) costs more than it returns, and an independent recall probe is how you measure whether escalation earned its cost.

## Step-by-step: running an evaluation

1. **Name the decision.** Write down the exact question ("ship model A or B?", "does this prompt change help recall?") and pick the matching approach from the table above.
2. **Establish an independent dataset.** Choose the dataset shape; ensure candidates do *not* come from the system under test; estimate prevalence if you're harvesting positives. **Freeze it** for the comparison.
3. **Fix the harness.** Drive the frozen headless CLI ([Part 5](agent-harness.md)); pin the model version; record the full config and dataset revision.
4. **Change one variable.** Hold inputs, queries, and every other parameter constant.
5. **Run each candidate multiple times.** Capture all artifacts; compute the spread, not just a point estimate.
6. **Score quality and cost together.** Pair the quality metric with a full-cost number from actual billing; bucket refusals/errors apart from quality failures.
7. **Calibrate any LLM judge** against a human sample; trust it only on the dimensions where they correlate.
8. **Decide, record, re-measure.** Log the decision and its evidence to the results trail ([Part 8](documentation.md)); after shipping, feed new failure forms back into the dataset.

## Name the anti-patterns out loud

Each of these *feels* like progress, which is why it's worth naming. Scan for them before you trust a result:

- [ ] **Grading your own homework**: gold built from the system under test.
- [ ] **"We added more patterns"**: a green suite proves only the cases you wrote down, and is silent on the fraction you never imagined.
- [ ] **The single run**: trusting one execution of a stochastic system.
- [ ] **Quality without cost**: declaring a winner on quality alone when the decision was always a trade-off.
- [ ] **Moving the goalposts mid-experiment**: adjusting thresholds/queries/gold while a comparison runs.
- [ ] **Demo-driven selection**: an example is not a dataset.

*Next: the loop has closed; what remains is what the change leaves behind. [Part 8. Documentation & knowledge capture](documentation.md).*

## See also

- [Part 6. Observability](observability.md), instrument before you tune; pair efficiency with quality.
- [Part 4. Three-layer model](three-layer-model.md), separately-evaluable layers.
- [Part 8. Documentation](documentation.md), recording the results trail.
- [Part 10. Data protection & privacy](data-protection.md), a dataset built from real inputs as a store of personal data, and redaction's quality cost as an eval dimension.
- [Handbook index](README.md).
