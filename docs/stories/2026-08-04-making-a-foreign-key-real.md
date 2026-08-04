# Making a foreign key real

## Context

The `*-audit` skill family is eight domain skills — architecture, CI, dependencies, docs, evals, prompts, security, tests — each auditing a codebase along one lens, all running on a shared engine that owns the loop. Under #543 we built a traceability matrix mapping every section of the engineering handbook onto that family, so "the handbook says X" can be checked against "some skill actually audits X". The [previous story](2026-07-30-calibrating-a-taxonomy-across-chunked-agents.md) covers adding a severity axis to that matrix.

Each matrix row recorded its coverage as a `{skill, dimension}` pair, where a *dimension* was a bolded phrase inside a numbered prose section of that skill's markdown file. This story covers #559 and #567, which turned that pair into a real key: one file per check, with the matrix and the skills validated against each other in both directions.

## Why

**The matrix's foreign key pointed at a table that did not exist.** Resolving `{skill, dimension}` meant parsing bolded phrases out of markdown bullets. Rewording a bullet in a skill silently broke every row citing it, and nothing anywhere would say so. We had built a coverage record whose integrity depended on nobody editing the thing it recorded coverage of.

**The skills had outgrown the shape they were written in.** All eight carried an identical seven-slot skeleton, and five of the seven varied per *check* while living in four different sections of one file. An agent auditing a single slice of a repo read the whole domain file first — between 2,300 and 4,800 words before gathering any evidence. An `/audit all` sweep paid that per domain, eight times over. Wave 1 of the epic (#542) then wanted to add TypeScript tooling alongside the Python (#519), which meant every Python audit would read TypeScript prose it would never use, and vice versa.

Doing nothing meant a coverage record that degraded silently as the skills it described were edited, and a family that got more expensive to run with every capability added to it.

## What

- **68 check records** across eight domains, each holding one check's claim, severity, detection procedure, fix patterns, review lens, and the matrix rows that ground it. 68 is the number the spec estimated before any of it was written.
- **Bidirectional referential integrity**, validated: a matrix row citing a check requires that check to name the row, and a check no row cites must carry a written argument for why. The two are views of one edge set, and the validator refuses to let them disagree.
- **All 80 matrix references** rewired from prose pairs to stable check ids.
- **Eight domain headers reduced from roughly 14,600 words to 5,100**, with the per-check content moved verbatim rather than summarised. Agents now load the records their slice needs.
- **Fan-out driven by data.** Each record declares whether it is decidable from one partition of the subject or needs the whole thing, and the engine slices on that rather than on a hardcoded axis.
- **The sweep front door detects which domains exist** from the checks tree instead of a fixed list, so a repo adopting three of the eight works without editing anything.
- **#567 then normalised the conventions** that drifted across the migration, and locked the two mechanically-checkable ones behind tests.

Three PRs, sequenced so each ends at a checkpoint where both reference forms still resolve and any single domain can be reverted. The third — deleting the legacy markdown-bullet parser — is still open.

## How

**Prose moved verbatim.** The migration's one hard rule: sentences move unchanged. Three edits were permitted — a dash style change, a leading label, and splitting a sentence at a clause boundary when it covered several checks. Reviewers diffed per-record word counts against the source sections and treated shrinkage as a defect. The point was not fidelity for its own sake: a migration that also rewrites is two changes, and when the result is wrong you cannot tell which one did it.

**The bidirectional rule did the reviewing.** It is the difference between a convention and a control. A half-applied change — citing a check without updating the check, or the reverse — fails the gate rather than shipping. This turned out to matter more than any instruction we gave an agent, because it is the only control in the whole exercise that does not depend on somebody looking.

**Parallel agents, per domain and then per file set.** The seven remaining domains were migrated by seven agents in one session; #567's normalisation ran as seven tasks partitioned by *file* rather than by issue item, because several items touched the same file and a file has to be owned by one task or two agents collide.

**Two-stage review per task, then a whole-branch pass.** Each task got a spec-compliance and a quality verdict from a fresh reviewer. After all of them, one reviewer on the strongest available model read the entire branch. That last pass is where the interesting findings came from, and it is not optional — see below.

## Findings

**A coverage gap that was never a coverage gap.** The matrix recorded one row as uncoverable with the note that the owning skill "declares no bolded dimension bullets so no matrix row can cite it". The coverage existed the whole time. Markdown had no way to express a citable unit, so the matrix recorded absent coverage that was present, and we had been reading that entry as a work item. Creating the two records closed it, and the residue narrowed to one clause that genuinely remains unchecked.

**A gap that had already been closed and was still recorded open.** A row about committing secrets carried a note prescribing "declare the history-and-rotation coverage" as its fix — work the migration had already done, by creating exactly that record. The note was false rather than merely dated. Fixing it moved a Critical unmapped clause off the head of the queue built in the previous story: that list is now three items, not four, and nothing was built to shorten it.

**Normalising in parallel slices relocated the drift instead of removing it.** This is the finding worth the story. #567 existed because seven parallel agents had produced convention drift across eight dimensions. It ran as seven parallel tasks, each passing its own review — and the whole-branch pass then found **four fresh instances of the exact defect class the branch existed to eliminate**, including a domain header offering a work-slicing axis that the shared engine explicitly forbids. Every task was individually correct. The defect lives between tasks, so only a reader of the whole thing can see it.

**A commit message that diagnoses a fix is not evidence the fix happened.** One commit's message described a contradiction precisely and correctly — and its diff renamed a noun, leaving the contradiction in place and arguably plainer. It survived a per-task review and a whole-branch review, and was caught only by a later reviewer whose assigned lens was reading git history, because that lens is the one that compares the message against the diff.

**Measurement falsified a rule we had written from a sample of one.** The engine recorded "about 520 words of body" as the family's header budget, measured when one domain had been migrated and then stated as a family rule. Three domains exceed it with nothing removable. The real driver is not check count — one domain carries eleven checks in 522 words while another carries seven in 587 — but whether the domain has a whole-subject check whose rationale must be stated.

**Three consecutive branches shipped false claims about themselves.** Fabricated measurement tables, a headline count of zero where the answer was one, a summary claiming nine records where eight changed. Each was caught by review, none by a gate, and each sat in prose *about* the work rather than in the work. The previous story ended by naming this exact failure mode; naming it changed nothing.

## Lessons learned

**Make the foreign key real and the gate starts doing the reviewing.** Every other control here depended on an agent following an instruction or a human noticing something. The bidirectional rule depends on neither: a half-applied edit does not merge. If a consistency property can be moved from prose into a validator, that is worth more than any amount of instruction, and it is the first thing to look for.

**De-drifting in parallel slices relocates drift rather than removing it.** A normalisation pass split across N agents is subject to the same failure as the migration that made the mess. Each slice can be internally perfect and collectively inconsistent, and per-slice review cannot see it by construction. Budget the whole-corpus pass into any parallel cleanup from the start, and expect it to find things — if it finds nothing, suspect the pass rather than celebrating.

**An artifact's expressive limits surface as false content, not as errors.** The coverage gap that was never a gap did not look like a formatting problem. It looked like a finding, phrased as one, and it had been sitting in a planning artifact being read as a work item. When a record says "nothing covers this", one of the live hypotheses has to be that the format cannot express the thing that covers it.

**A count in a scoping document is a licence not to recount.** Our plan asserted that eleven surviving instances of a term were all benign. There were twelve and four were not, and one was misrouting agents. The wrong number was not the damage; the damage was that a measured-sounding figure in a *scope* tells every later reader the counting is done. An unverified figure in commentary is a false claim. The same figure in a scope suppresses the check that would have caught it.

**Writing a lesson into a retrospective does not install a control.** We ended the last story by saying to point quality controls at the prose and not only at the data. We then shipped five more instances of exactly that across two branches. A lesson at the end of a story has about the enforcement power of a comment. The version that works computes the figure from the data or does not assert it.

**Once-ness has to be structural, not instructed.** One check was decidable per-partition except for a single repo-wide fact, handled by telling agents to "report this once for the repo, not once per package" — which asks N independent parallel agents to coordinate, something they cannot do. Splitting it into a per-partition check and a whole-subject check made the once-ness a property of the data. Any instruction that requires parallel agents to agree about what the others are doing is a bug report about the decomposition.

**Test what is mechanical and leave judgment to people, but make sure the test locks what it claims.** Of this work's eight normalisation items, exactly two stated a rule with no judgment call, and only those got tests. That restraint was right — a test encoding a judgment call becomes a thing to satisfy. But the first version of one test asserted something strictly weaker than the convention it documented, and would have passed a regression straight back to the old form. A test that cannot fail on the thing it names is worse than no test, because it advertises a guarantee it does not provide.

## Open questions

- **Does record-per-unit generalise past audits?** The pattern — take the thing a document repeats per item, give each item a file, validate the references both ways — is not audit-specific. Prompts, evals and SOPs all have the same shape today. Whether the win survives contact with a corpus that has fewer natural "checks" is untested.
- **Can the reporting-defect class be gated at all?** Every instance was a number asserted in prose that nobody recomputed. A gate would need to know which figures in free text are claims about the repository. Cheap partial answers exist — forbid bare digits in specific fields, require a reproducing command beside any count — and none has been tried.
- **How much did the two-stage-plus-whole-branch review structure actually buy?** It caught real defects at every level, but we have no counterfactual. We do not know whether the whole-branch pass would have found the per-task findings anyway, which is the number that would tell us whether per-task review earns its cost.
- **Is the migration reversible in practice?** We sequenced three PRs so any single domain could be reverted at a checkpoint. Nobody has tried, and an untested rollback path is a belief rather than a property.

## What's next

- PR 3 of #559 retires the legacy markdown-bullet parser. Nothing cites the old form; it is a deletion.
- #567 is in review; #568 records a fix pattern a domain detects but cannot repair, found because the migration forced detection and remediation into one record for the first time.
- The head of queue from the previous story is now three Critical unmapped clauses, feeding #544, #516, #548 and #550.
- Wave 1 of #542 can now add TypeScript tooling as a per-record field rather than a rewrite, which was the original point.
