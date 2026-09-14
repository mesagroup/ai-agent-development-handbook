---
id: eval/run-variance
domain: eval
locality: global
handbook:
  - agent-harness/offer-cheap-and-mock-backends-a-fast-inner-loop-is-a-discipline
  - evaluation/measure-honestly-a
  - evaluation/name-the-anti-patterns-out-loud
---

# Run-to-run variance

Are the reported numbers produced by repeated runs, with the run-to-run spread reported beside them? A single run of a stochastic system is one sample of it, and a figure with no spread beside it cannot say whether a difference is real. The form the spread takes follows the case type rather than a fixed list: a scalar score carries a spread across runs, and a pass/fail case carries its reliability band over N runs plus the strict all-N-pass aggregate, because an average of lucky runs answers a different question from "will this work every time".

## Severity

**Important** - a headline number, or a candidate-versus-candidate comparison, reported from a single run.

**Important** - a claimed improvement whose margin sits inside the spread the project itself reported. This is the project's own numbers contradicting its own conclusion, and the evidence is both figures side by side.

**Minor** - the runner produces repeated runs but the reported artifact carries only the mean, so a reader of the leaderboard cannot see the spread that exists.

## Tooling fallback

Needs reading - no tool in this domain's evidence pass reaches this: read the eval runner for whether it executes each candidate more than once, and the leaderboard or report artifact for whether a spread travels beside each number. The evidence pointer is the reported figure and its spread, or the reported figure and the absence.

**This check brings no threshold of its own.** A project that reports its spread has satisfied the claim whatever the number is, and how high a reliability bar must sit is a business decision tied to the change's criticality, which the handbook says and this check does not second-guess. Where the project has set its own bar, whether it applied it is read against that bar and never against one the audit supplied. The single judgement this check makes is internal to the project's own figures: a claimed margin smaller than the project's own reported spread.

**The three neighbours, and what each keeps.** `eval/methodology` owns whether the instrument tracks quality and whether N is large enough to distinguish candidates - the under-powered eval is its finding, and this check does not re-ask it. `eval/reproducibility` owns whether a number can be regenerated: pinning the model, the config and the seed makes an anecdote repeatable rather than making it a measurement, so a project can be fully reproducible and still fail this check. `eval/regression-tracking` owns whether results are tracked across changes at all.

## Fix

**Run each candidate several times and carry the spread into the reported number**, in the form the case type calls for. Where a comparison is the point, run it until a real difference would clear the noise band rather than reporting the first margin that appears. **What closes it is the distribution, not a passing run.** The domain gate offers a smoke or eval run, and one run is exactly what this finding says is insufficient - it can come back green over a result that still carries no spread. The close is the repeated run and the spread it puts beside the number, so state that as the gate rather than inheriting the domain's default.

## Review lens

**Variance honesty** - is the reported spread measured across repeated runs of one candidate, on the candidate as it ships? (Highest-value catch: a spread computed across the cases in the dataset rather than across runs, which is a different quantity wearing the same name and is flattered by an easy case mix.)
