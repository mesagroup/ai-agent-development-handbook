# `audit-core` obligations and how the sweep discharges them

The `audit` skill is the multi-domain sweep front door. Its step 0 states that the sweep "substitutes its own steps for the `audit-core` loop rather than running it, so it inherits none of that step implicitly" — which is a promise to restate every obligation it needs. A promise of that shape is not checkable by reading either file alone: `audit-core` states the obligation, `audit/SKILL.md` is where it is kept or dropped, and a dropped one is invisible because nothing in the sweep's text refers to what is missing from it.

This is that check, written down so it can be re-run rather than re-derived. One row per obligation `audit-core` states, with the disposition the sweep has chosen and where. Rows whose disposition is not **restated** are the interesting ones: each is a place the sweep deliberately diverges, and the "how" column is where that divergence is justified.

## Dispositions

| Disposition | Meaning |
|---|---|
| **restated** | `audit/SKILL.md` carries the same rule in its own words. |
| **adapted** | The sweep states a deliberately different rule, and says why in its own text. |
| **delegated** | Discharged by the `<domain>-audit` skill the sweep dispatches, which runs the real `audit-core` step. The sweep must not restate it, because restating it would give a domain agent two authorities for one rule. |
| **out of scope** | The sweep never reaches the obligation. Either it never reaches the step carrying it - report-only and fix-delegating, so the remediation half of the loop is structurally unreachable - or it reaches the step but the obligation exists to serve a later one it does not run. Both cases must name which, because the second is the one that can be wrong: an obligation that turns out to earn its keep at diagnosis time is a dropped obligation wearing this label. |

## How to re-run this check

Read `.agents/skills/audit-core/SKILL.md` whole — not a diff — and for every sentence that tells a run to do something, find the row here. An obligation with no row is the defect this record exists to surface; add the row and either restate the obligation in `audit/SKILL.md` or record why it is not restated.

`tests/test_sweep_obligations.py` checks the half that can be mechanical: every anchor below occurs in `audit-core/SKILL.md` exactly once, every row carries a disposition from the vocabulary table above (parsed from this file, so the two cannot drift) and a non-empty justification, and every quotation in this document is verbatim from one of the two files. That catches the staleness mode this record is most exposed to — one of those files reworded, and the ledger silently stops describing it. Exactly once rather than merely present, because these anchors are short: a phrase that reappears in a later recap would let a row keep passing while the sentence it was written to pin got rewritten.

It also guards against the failure that would make all of the above worthless: a ledger the parser walks only part of, leaving a green suite behind while most rows go unexamined. Every table in this file must be one the parser recognises, no table row may be orphaned from its table, and an unreadable row is reported rather than skipped. Grouping the obligations under sub-headings is safe; a stray blank line inside a table is not silent.

What none of it can check is whether a disposition is *true*. That is the reading pass above, and it is the only thing here that catches a dropped obligation.

## The obligations

| Obligation | `audit-core` anchor | Disposition | How the sweep discharges it |
|---|---|---|---|
| Evidence comes from the real artifact | `never from a summary, a stale doc, or an assumption` | restated | The fan-out brief requires verifying each finding against the real artifact so scanner artifacts do not become findings; repeated as a cross-cutting rule. |
| Announce the skill and subject | `Announce (from the domain skill):` | adapted | The sweep announces itself and its report-only mode, not a domain lens, because no single domain owns the run. |
| Pin every subagent to the tree under audit | `require each agent to confirm its own` | restated | The dispatch list passes `target_root` *and* requires each agent to confirm its own `git rev-parse --show-toplevel` matches before it reads. |
| Fix the subject and the depth at scope time | `Fix the subject (which package/tree/config) and the depth` | adapted | The sweep's subject is a set of domains rather than a tree or a config, so scope is argument-first over the domains available as this skill's own siblings, with a named domain that has no records reported as skipped rather than dropped. Depth is not a variable here: breadth at a fixed depth is what distinguishes the sweep from the per-domain run. |
| Ask the user the mode | `Always ask the user the mode:` | adapted | Report-only by default and only asks about fixes if the user raises them, because a sweep that fanned fixes out would collide on shared files. |
| Deliver a large fix subject in increments | `deliver in **increments** (one coherent slice per PR)` | out of scope | The sweep runs no fixes; the domain skill it hands the work to owns the increment shape. |
| Resolve the opt-in sub-audits at scope time | `Resolve any opt-in sub-audits here too` | restated | Step 0 resolves them once for every selected domain and passes each domain its granted list, since parallel agents have nobody to ask. Split by what the opt-in produces: an opt-in *check* yields findings rows and is resolvable here, while an opt-in *deliverable* emits an artifact and is out of scope for a report-only sweep, offered in step 4 instead. |
| Resolve `target_root` explicitly | `resolved to a real path` | restated | Step 0, named as never inferred from the working directory. |
| Resolve `target_ref` | `the branch name, and whether the tree is dirty` | restated | Step 0; the report template's "How the audit ran" reproduces it. |
| Refuse an `out_path` under the target | `refuse any path that resolves under` | restated | Step 0, and again inside the output step where the Markdown option names the path, plus once as a cross-cutting rule. |
| The report is always also returned in conversation | `always returned in conversation as well` | restated | Step 0 states it, so a run given no path is never silent. |
| A non-interactive run defaults to conversation only | `A non-interactive run defaults to conversation only and writes nothing` | restated | Step 0 and step 3 both state the default and both allow the file when the invocation supplied a path. |
| Fan out read-only agents in parallel | `fan out read-only subagents in parallel` | restated | One read-only agent per selected domain, concurrently, with a barrier before consolidation. |
| Run the domain's detection tooling in the evidence step | `Run the domain's detection/measurement tooling here` | restated | At length, because the sweep adds a constraint the engine does not carry: the tooling must run without adding a dependency to the target. That bullet covers the one-shot runner per package manager, the three kinds of thing a `tooling:` entry can name and which of them a runner can reach, preferring what the inventory reports already installed, recording the resolved version of anything fetched, and `no-evidence` for the rest. |
| Build a shared ground-truth artifact once | `rather than each rebuilding a possibly-inconsistent copy` | restated | The sweep is where the saving is largest, so it builds the inventory before anything fans out. |
| The first shared artifact is the project inventory | `The first such artifact is always the project inventory` | restated | Named as such, with its fields enumerated in the bullet that passes it to every domain. |
| A partition's language is a set, detected by census | `Detect by a file census plus declaration files` | restated | Stated where the sweep builds the inventory, because a domain agent handed the artifact cannot re-derive what it was given. |
| Match the fan-out axis to each check's locality | `Match the fan-out axis to each check's *locality*` | delegated | The sweep's own axis is one agent per domain; each domain agent is told to fan out internally by `locality`. |
| Do not give a cheap local check its own agent | `Do **not** fan a cheap local check out to its own agent` | delegated | Stated by the sweep to be the domain skill's internal concern. |
| Gather the project's conventions for house style | `so remediation matches house style` | out of scope | The purpose is matching remediation to house style, and the sweep remediates nothing. |
| Every matrix row carries an evidence pointer | `plus a one-line evidence pointer` | delegated | Domain agents build the rows; the sweep merges them and its template fixes the columns. |
| The `handbook` cell is read from the record | `so the matrix introduces no new source of truth` | delegated | Same: the sweep merges matrices rather than deriving cells. |
| Cite a stable identifier, never a line number | `never a line number, for the reason the record schema already gives` | delegated | Same. |
| Clean, `no-evidence` and `not-applicable` never collapse | `three outcomes are distinct and must never collapse into one another` | restated | In the fan-out brief, and again as the coverage column the roll-up table requires. The brief also asks each domain to return its coverage triple as a count, because the matrix it returns is capped to the significant rows and a `no-evidence` row is not one: recounting coverage downstream from the returned rows would report zero of everything for a domain that answered nothing. |
| Severity scale and counts | `Severity is Critical / Important / Minor. Summarize counts.` | restated | Fixed by the report template's roll-up. |
| The no-writes-to-the-target rule is unconditional | `it holds when the audited repository is the one asking` | restated | The output step carries it in that wording where it names the Markdown path, and again in its own words where it permits the write at all. |
| Record policy decisions so they are not re-litigated | `record any policy decisions so they are not re-litigated` | restated | The template's "How the audit ran" section is the record: scope, mode, lens SHA, tool log, verification note. |
| Report-only stops after the matrix | `If the mode is report-only, stop here` | restated | The sweep has no later step to stop before; it presents, then offers fixes without running them. |
| Present a recommended-remediation sketch | `with a short recommended-remediation sketch` | restated | Its own section in the report template, one line per domain, bounded to the smallest change that retires that domain's most severe row. The sweep is always report-only, so this is the one obligation of the report-only branch it can never avoid owing - and it is a sketch, not the plan, which is the engine's step 3 and belongs to the per-domain run. |
| Steps 3 to 6 run only in fix mode | `run only in report + fix mode` | out of scope | Plan, apply, whole-branch review and PR all belong to the domain skill the sweep delegates to. |
| Every finding cites what it rests on | `Every finding and every fix cites the artifact/tool output it rests on` | restated | A cross-cutting rule, with the added constraint that consolidation must not weaken it. |
| Cross-link rather than duplicate | `one owns it and the other links` | out of scope | An authoring-time rule about which skill owns a topic, not something a run does. |
| Never fabricate a source, URL, licence or advisory id | `Never fabricate a source, URL, license, or CVE id` | restated | Twice, because it has two halves the sweep needs separately: do not upgrade a severity or invent a finding during consolidation, and carry every identifier a domain reported rather than supplying a plausible one to complete a row. Consolidation is where this bites, being the step that strips the tool output an id came from and then republishes the id in three formats. |
| Fix pre-existing issues you touch | `Fix pre-existing issues you touch` | out of scope | The sweep touches nothing. |
| Keep the domain gate green per task | `Keep the domain gate green per task` | out of scope | No tasks and no commits. |
| No environment-specific values in emitted artifacts | `placeholders with prose explaining what they resolve to` | restated | A cross-cutting rule covering every emitted report. |
| Check the no-writes invariant rather than promise it | `and again after the matrix is built` | restated | `git status --porcelain` before and after, with the delta as a line in the report template. |
| Discover the target's layout rather than assume one | `Discover packages/layout/tooling/conventions from the target repo` | restated | The inventory is exactly this discovery, built once before the fan-out; the cross-cutting rule extends it to detecting the available domains from the skill's own siblings rather than from the target. |
| Impose a standard only if none exists, and confirm it with the user | `impose a standard only if none exists, and confirm it with the user` | adapted | The sweep authorises no inferred rubric at all, rather than inferring one and confirming it: a dispatched agent has nobody to confirm with, so step 0 tells it to report the absence of a documented rule as the finding and to flag no violations against one it invented. Stated as a deliberate divergence because a directly-invoked domain run, which can ask, should still infer and confirm. |
