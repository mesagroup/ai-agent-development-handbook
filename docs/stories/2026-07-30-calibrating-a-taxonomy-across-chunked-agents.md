# Calibrating a taxonomy across chunked agents

## Context

The engineering handbook (`docs/engineering/`) is our project-agnostic account of how we build software and AI agents. It is twelve parts long, and it is normative: everything in it is meant to be a directive somebody could be held to. Under lidia-tech/lidia-agents#543 we built a traceability matrix that maps every one of its sections onto the `*-audit` skill family, so that "the handbook says X" can be checked against "some skill actually audits X". That matrix shipped in lidia-tech/lidia-agents#549 as 124 rows, each carrying a *class* — `static`, `artifact`, `process` or `informative` — recording whether the clause can be checked at all, and, where nothing checks it, a gap entry saying so.

This story covers lidia-tech/lidia-agents#552, the follow-up that added a second axis. It is worth writing down less for the axis than for what happened while we filled it in: 108 judgment calls, spread across five independently-run agent batches, against a definition that turned out to be underspecified in ways nobody could have enumerated in advance.

## Why

The class axis answers *can we see it*. It cannot answer *does it matter*. The consequence was a 67-row gap list in reading order, where a clause about committing secrets sat next to a clause about docstring formatting with nothing to tell them apart. That is a list nobody can act on.

The concrete cost was to the work the matrix exists to feed. #1's productionization roadmap needs to know what to sequence first. The audit-domain issues that inherit the gap list (#7, #2, #11, #12) each need to know which of their gaps is the urgent one. Without a risk axis, all of that ordering falls back to handbook reading order, which is an accident of exposition.

Doing nothing meant shipping a coverage record that was complete and unusable.

## What

- A `severity` axis on every matrix row: `critical`, `important` or `minor`, reusing audit-core's existing three bands rather than inventing a scale, so a matrix row and an audit finding need no translation at any seam.
- 108 severity ratings — every row except the 16 `informative` ones, which are non-normative and correctly carry none.
- Validation making the axis structural rather than advisory: severity required on assessable rows, forbidden on informative ones, and (the load-bearing one) a gap forbidden on an informative row, which is what makes the rendered gap list's three severity groups exhaustive so no gap can silently vanish from the page.
- A severity-by-coverage cross-tab in the rendered matrix, which is what converts the gap list into a work queue.
- `docs/engineering-notes.md`, a new advisory sidecar deliberately outside the handbook, holding practices too contingent on one execution environment to be normative, each recorded with the environment it applies to and why it was cut.
- A written record of the calibration rules the sweep produced, in the plan under `docs/superpowers/plans/`.

## How

**Reusing a scale instead of designing one.** The temptation was to design bands fitted to handbook clauses. We took audit-core's instead. A matrix row and an audit finding then mean the same thing by "Important", and no consumer has to translate. The cost is that the borrowed definitions were written for findings about a codebase, not for clauses about practice, and most of the calibration work below is that mismatch surfacing.

**Severity as a baseline, not a verdict.** A row's severity is the risk that violating the clause carries in general, not a judgment about this repo. An auditor may raise or lower it for a specific instance with a stated reason. This matters for the tie-break rule below.

**Sweeping before changing the schema.** The renderer ignored unknown keys, so the ratings were invisible until the last task. Every intermediate commit stayed green without the field having to be optional-then-required, and without the staged scaffolding that an earlier review had removed under the no-stubs rule.

**Chunking, and the problem it created.** The handbook does not fit one agent's working context alongside the matrix and the audit skills. So the sweep ran as five per-part batches, each a fresh agent, each reviewed against the handbook prose rather than against its own diff. The identified risk going in was calibration drift: one agent's Important is another's Minor, and a merged artifact of 108 ratings that are not mutually comparable looks exactly like one that is.

The controls we used, in the order they earned their place:

1. **Settle once, then lift.** Every calibration question was resolved by argument and then written into the plan's Global Constraints, which every subsequent batch read. Answering the batch that asked would have fixed one row and lost the rule.
2. **Pinned anchors.** Nine rows were pre-rated with the reasoning shown, and shipped in every batch brief. A definition is interpretable prose; an exemplar pair with the distinction spelled out is much harder to read two ways.
3. **A mandatory doubts section.** Every batch report had to carry one. An agent's default is to resolve an ambiguity quietly and move on, which is precisely the behaviour that produces drift. Most of the rules below came out of that section.
4. **A handoff check.** Added mid-sweep, after one batch rated three rows on the *residue* left over from handing part of a clause to another row. Rating both ends of a handoff and comparing them found a matrix note that named one owner for a clause that had two.
5. **A final whole-corpus pass.** Because the earliest batches ran under a thinner rulebook than the last, and nothing else would revisit them.

**What the rules turned out to be.** Seven accumulated. Three are about the severity scale; three are about *which row owns which clause*; one is a general escape hatch.

| Rule | What forced it |
|---|---|
| Rate a row at the max over the clauses it owns | A row whose claim bundles several clauses. The first batch applied two incompatible readings *within itself* |
| "Unbounded cost" means one run that can run away with no ceiling, not a recurring tax | Every compounding engineering cost was arguing itself into the Important band |
| A structural clause is `minor` unless the violation makes a behavioural change invisible to a dependent party | Layering and decay clauses had no principled band |
| A gate is `critical` only when the harm it is the *sole* detector for is itself Critical | "Other barriers still stand" was being used by a clause that was the only barrier |
| Critical is a consequence band, not a security band | Security-flavoured clauses drifting up, consequence-heavy non-security clauses drifting down |
| A documentation-currency clause is `important` only when the stale claim is the reader's only access to the truth | Documentation clauses splitting arbitrarily |
| Before writing `important`, name the specific thing you can no longer tell | Catch-all. If the honest answer is "it costs more, takes longer, or reads worse", it is `minor` |

The first rule needed four qualifiers before it held, three of them added by later batches hitting cases the first had not: a clause another row owns raises that row rather than this one; a pure recap row owns nothing of its own and takes the max of what it recaps; a matrix note that divides a claim settles ownership; and a second imperative statement of the same rule is ownership, not a cross-reference.

We chose max-over-clauses rather than an average deliberately. Severity is a baseline an auditor can lower with a reason, so over-rating is recoverable while under-rating buries a high-risk clause where the cross-tab never surfaces it. When raters will disagree anyway, pick the tie-break whose failure mode you survive.

## Findings

**The distribution, and the answer it produced.** 12 Critical, 75 Important, 21 Minor across 108 assessable rows.

| Severity | Fully mapped | Partial | Unmapped | Auditable total | Process |
|---|---|---|---|---|---|
| Critical | 4 | 0 | 4 | 8 | 4 |
| Important | 14 | 17 | 29 | 60 | 15 |
| Minor | 2 | 4 | 13 | 19 | 2 |

Four Critical clauses are auditable and nothing checks them: agent-harness bounding, agent least-privilege, secrets-in-history and rotation, and data-protection accounting. That is a four-item head of queue, and the class axis alone could not produce it. Four names is a modest-sounding return for 108 ratings, and it is the honest one for *this axis*. The calibration machinery is a second deliverable, and probably the more reusable of the two.

**The drift we measured is likely a floor, not a typical case.** We did not design a scale. We borrowed one that audit-core had already exercised against real findings, with its bands and their boundaries written down and in use. That is close to the best starting position a chunked classification can have, and it still took seven rules, four qualifiers on one of them, and a mid-sweep handoff check to hold 108 ratings together. The working intuition — speculation, and flagged as such — is that the looser the initial taxonomy, the more of the final ontology gets discovered during the sweep rather than before it, and the more this machinery earns. On that reading the interesting counterfactual is not what calibration cost us here, but what merging five uncalibrated batches would have cost against a scale nobody had used before.

**Expected: the bands would need sharpening.** They did.

**Surprising: half the rules were not about severity.** Three of the seven govern which row owns which clause. Chunking a document is not only splitting text — it partitions a claim space, and clauses straddle the partition. Every rater on each side of a boundary has to decide whether a straddling clause is theirs, and if the instructions are silent, two reasonable agents will silently answer differently. We went in expecting to calibrate a scale and spent about half the effort calibrating ownership.

**Surprising: the sharpest ambiguity detector was a single agent contradicting itself.** The first batch rated two structurally identical rows differently *inside one batch*. That is proof the ambiguity lives in the instruction rather than in the rater, and it arrived from batch one, without waiting for a second batch to compare against.

**The controls held.** The final consistency pass over all 108 rows found no cross-batch inconsistency, including 8 for 8 on the recap convention — the case that needed the most qualifiers.

**Where the process still leaked.** A full review of the finished branch (five independent reviewers, findings scored, seven above the posting threshold) found that four of the seven were untrue or soon-to-be-untrue statements in prose the branch had written about itself: two hardcoded counts in the rendered legend, an overclaim in the sidecar contradicted by the matrix cited in the same sentence, and a docstring narrower than the function it described. A branch whose subject was *making a document's claims true by construction* shipped four claims that were not. The calibration controls were pointed at the ratings, and the prose around them had none.

**The one real defect was a silent pass, again.** The sidecar's link from the handbook was relative, and the handbook ships as a self-contained single-page artifact whose link resolution covers in-handbook targets only. The link worked on GitHub and was dead in the artifact. Neither documentation gate could see it, because that tree is excluded from the site build, and the renderer's own signal was a printed warning. Same shape as the three silent-pass bugs lidia-tech/lidia-agents#549 had already closed, one directory over.

## Lessons learned

**A classification scheme is not underspecified in the abstract; it is underspecified relative to a corpus.** You cannot enumerate the distinctions you failed to draw until the corpus presents them. Trying to write a complete rubric up front is the wrong goal, and time spent there is better spent on the machinery that makes mid-sweep discoveries converge.

**The failure mode is silent divergence, not disagreement.** Two agents visibly disagreeing is cheap and self-announcing. Two agents each quietly resolving the same ambiguity in different reasonable directions, both reporting success, is the expensive one, because nothing in the merged artifact flags it. This is the same class as a parser that drops a row without erroring, and it deserves the same suspicion.

**Within-batch self-consistency is a cheaper ambiguity detector than cross-batch comparison.** One agent rating two like items differently inside a single batch localizes the fault to the instruction immediately, and it is available from the first batch rather than the second. Ask every batch to check itself for it.

**Adjudications must be lifted into the shared rulebook, not delivered to the batch that asked.** The rulebook is the accumulating ontology and it should grow monotonically through the sweep. A ruling that lands only in one batch's reply fixes one item and loses the rule, and the next batch pays for it again.

**Anchors calibrate faster than definitions.** A handful of pre-rated hard cases, with the distinction between them made explicit, does more than another paragraph of criteria. Prose invites interpretation; a worked pair constrains it.

**Force the doubts to surface, or they resolve themselves invisibly.** A mandatory doubts section in every batch report converts silent resolution into a reported question. It is nearly free, and it is where most of our rules came from.

**Ask for the discriminator, not the label.** Rules that require the rater to *name* something — the specific thing you can no longer tell, the party the change becomes invisible to — turn a vibe into a falsifiable claim a reviewer can check. Rules phrased as adjectives do not.

**Choose the tie-break whose failure mode you can survive.** When raters will disagree at the margin regardless, the question is not which answer is right but which error is recoverable. Over-rating a clause is visible and adjustable; under-rating it removes it from the queue where anyone would look.

**Chunking partitions a claim space, not just text.** Budget rules for boundary-straddling items and for ownership, not only for the classification itself. This was the biggest surprise and it is the least obvious thing to prepare for.

**Early batches run under a thinner rulebook than late ones, and nothing revisits them by default.** That asymmetry is structural to any accumulating-rules approach. Plan the final whole-corpus consistency pass into the schedule up front rather than discovering you need it.

**Point the quality controls at the prose too, not only at the data.** Every control we built guarded the ratings. The commentary explaining the ratings had none, and that is where the review found the untrue statements. Any figure asserted in generated prose should be computed from the data or removed, and the same discipline applies to the summaries humans write around a dataset.

## Postscript: what the next two sweeps showed

*Added 2026-08-04, after lidia-tech/lidia-agents#559 and lidia-tech/lidia-agents#567 restructured the same audit family onto a checks database. That arc has its own story in [Making a foreign key real](2026-08-04-making-a-foreign-key-real.md); recorded here only where it scores a claim this one makes.*

**One of the four Critical unmapped clauses is now mapped, and the route was not the one we expected.** The head of queue is three, not four: secrets-in-history-and-rotation dropped off. Nothing was built to close it. The coverage had existed the whole time inside `security-audit`, and the matrix could not cite it because markdown had no way to express a citable unit — the gap was in the *expressive power of the artifact*, not in the skill. Turning each check into its own record made the coverage addressable, and the row now cites it. We had read that row's gap note as a work item for a year of planning; it was a formatting limitation wearing a work item's clothes. Worth carrying forward as a caution: a coverage record can under-report coverage for reasons that have nothing to do with coverage, and the taxonomy will not tell you which entries those are.

**The prose lesson recurred twice, immediately, and that is the useful part.** This story's last lesson — point the quality controls at the prose, not only at the data — was written after review found four untrue self-descriptions here. In the two sweeps since, in the same family:

| branch | false claims in prose about the work | caught by |
|---|---|---|
| lidia-tech/lidia-agents#552 (this one) | 4: two hardcoded counts, an overclaim contradicted by the artifact cited in the same sentence, a too-narrow docstring | whole-branch review |
| lidia-tech/lidia-agents#566 | 2 notes whose line-number citations were invalidated by their own edit | whole-branch review |
| lidia-tech/lidia-agents#567 | 3: fabricated word-count deltas, a "0 substantive corrections" headline when the answer was 1, a "9 records" count when it was 8 | per-task review, whole-branch review, and the post-PR review pass |

Every instance was caught by a reviewer and none by a gate. The diagnosis we did not make the first time is the one that matters: **writing a lesson into a story does not install a control.** We stated the rule at lidia-tech/lidia-agents#552, believed it, and then shipped five more instances of exactly it across the next two branches. Advice at the end of a retrospective has roughly the enforcement power of a comment. The version that would have worked is structural — computing every asserted figure from the data, or refusing to assert it.

**A scoping document that states a count is a licence not to recount.** lidia-tech/lidia-agents#567's plan carried an out-of-scope entry reading "the eleven ordinary-English uses of *dimension* ... are correct English and correct domain vocabulary." There were twelve, four of them were not ordinary English, and one of the four was actively misrouting agents. The count was wrong, but the damage was not the wrong number: it was that a measured-sounding figure in a scoping note tells every later reader the counting has already been done. This is the sharper form of the lesson above. An unverified count in commentary is a false claim; an unverified count in a *scope* is a false claim that suppresses the check that would catch it.

**The looseness question got its first data point, and it points the way the intuition guessed.** We noted that we had borrowed a mature scale, and wondered how much more the calibration machinery would earn against a taxonomy invented for its corpus. lidia-tech/lidia-agents#559 is a partial answer from the loose end. Its record schema was invented one PR before the sweep that used it, versus audit-core's severity bands which had already been exercised against real findings. Seven parallel agents against the newer schema drifted across eight separate convention dimensions — enough that normalising them needed its own issue, its own plan, and its own seven-task sweep. That is not a controlled comparison and we should not treat it as one, but it is the predicted direction, and the cost landed roughly where the intuition said it would.

## Open questions

- **Does the three-band scale need a fourth?** Four parts showed the same pressure: a harm that is neither exposure nor loss of measurability, but a cost that grows. We decided against adding a band, on the evidence of the cross-tab's own distribution — the Important band's largest homogeneous cell is small enough that severity never has to break a 75-way tie, and Critical-plus-unmapped is already a crisp four-row queue. A fourth band would buy a certain translation cost at every audit-core seam for a distinction no consumer can currently act on. Worth revisiting if a consumer appears that can.
- **Where should structural-debt magnitude live, if not here?** The pressure above is real even though the band is not. No field in this matrix should carry it, because `arch-audit` already owns that ranking. Whether the two records should reference each other is open.
- **How much does the payoff scale with the looseness of the starting taxonomy?** We borrowed a mature scale and still needed seven rules, so the machinery paid for itself at what should be the easy end of the range. The intuition is that a scheme invented for its corpus would push more of the ontology's discovery into the sweep, arriving later and costing more to retrofit — which would make lifting, anchoring and the final pass more valuable rather than less. Testing it needs a second sweep against a taxonomy designed from scratch, and a way to measure drift that does not depend on the same coordinator who wrote the rules.
- **Can the ownership rules be generalized?** Three of our seven rules are about clause ownership across a partition. They read as though they would transfer to any chunked classification, but we have one corpus and one sweep. It would take a second, unlike corpus to know whether they are general or ours.
- **How much of this survives without a human adjudicator?** Every rule here was settled by argument between the coordinating agent and a human, and lifted by hand. Whether a coordinator can adjudicate and lift reliably on its own — and how you would detect it adjudicating badly — is untested.

## What's next

- lidia-tech/lidia-agents#551 completes wave 0 of the #1 epic; the coverage-floor clause still has open design questions.
- lidia-tech/lidia-agents#553 and lidia-tech/lidia-agents#554 are filed against the matrix itself: the gap list cannot yet distinguish an unchecked row from a partial row's residue, and the coverage summary can contradict itself in a shape that has zero instances today.
- The four Critical unmapped clauses are the head of queue for #7, #2, #11 and #12.
- Whether the transferable half of this story becomes a handbook section is undecided. It would need matrix rows, a class and a severity of its own, which is now a known and non-trivial price.
