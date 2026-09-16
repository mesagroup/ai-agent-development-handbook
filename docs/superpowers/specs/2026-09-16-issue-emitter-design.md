# The issue emitter (#9)

**Status:** approved 2026-09-16, self-approved under autonomous mode on Janos's behalf, per the sixth nightshift loop's wake prompt. The reasoning is here so the approval can be reversed by reading rather than by re-deriving.

## Problem

The audit family produces two deliverables and ships one. The prose report exists and has a template; the importable issue set exists only as a shape a human once produced semi-manually, which means every future audit re-derives the clustering, the titles and the parent links by hand and gets a different answer. `docs/goal.md` makes the emitter the whole of O3 and a prerequisite for O4's reviewed dry-run issue set, so this is the deliverable's second half rather than tooling around it.

## The input is not the report

The obvious input is the consolidated report's per-domain findings matrix, which is a pipe table with fixed columns: `Item | Check | Status | Severity | Evidence | Handbook`. It is the wrong input, for a reason the report template states about itself: the table is **"capped to the significant rows"**. It is a human-facing summary that drops rows on purpose, so an emitter reading it produces an issue set missing exactly the findings the report judged too minor to print, with nothing to say they were dropped.

A second reason reinforces it. This repository spent an epic (#58) moving the harness off prose-parsing, on the finding that inferring structure from typography approximates and every defect in that family was a patch on the approximation. A pipe table is more structured than a backtick span, so this is not the same defect, but the direction of travel is settled and an emitter that parses the report would be moving against it.

**So the sweep emits a findings file, and the emitter reads that.** The report stays what it is. The findings file is the complete set, in the order the sweep produced it, and the report is a rendering of the significant part of the same data. Where the file is absent, the emitter says so rather than falling back to the report, because a fallback that silently drops rows is the failure this decision exists to avoid.

## What it emits

Three levels, which is the precedent's shape:

- **One top-level epic** per audited repository.
- **One child epic per domain** that has at least one finding. A domain with no findings gets no epic, because an empty epic in a tracker reads as work rather than as a clean result; the report carries the clean domains.
- **Sub-issues clustered**, never one per finding. A hundred-finding audit that emits a hundred issues is not a work plan, it is the report again in a worse format.

## Clustering rule

**One sub-issue per (domain, check, severity).** A check is one question, so its findings share a fix and belong together; severity splits them because a Critical and a Minor answering the same check get different priorities and are scheduled apart. Every finding in a cluster becomes one evidence line carrying its `file:line`, and the cluster's body carries the handbook citation once, since a check cites the same clause whatever it found.

Three properties follow, and they are what the tests hold:

- Two findings of the same check at the same severity are one issue. This is the merge case.
- Two findings of the same check at different severities are two issues. This is the split case.
- A finding's evidence is never dropped, whatever the clustering: the count of evidence lines across all issues equals the count of findings in.

The rule is deliberately mechanical rather than semantic. An emitter that clustered by "related root cause" would be making a judgement the sweep already made and recorded as the check id, and a second judgement that disagrees with the first is how one finding ends up in two issues.

## Creation is behind a flag, and default is dry run

The emitter prints the full tree by default and creates nothing. Creation requires an explicit flag, and the label-creation path is part of that flag rather than a separate convenience: creating a label is a write to the target repository, and a tool that writes on its default path is one a reader will run against the wrong repository once.

Nothing in this change exercises the creation path, and no test does either. That is the whole of the caution: writes go to a repository this project does not own, and an unattended loop is not the thing that should first perform one.

## Verification

- Unit tests over the pure logic - clustering, body rendering, tree building, label derivation - loaded the way this repository loads script helpers, with `scripts/` on `sys.path` via the tests' conftest.
- The three clustering properties above, each as its own test, including the conservation property that no evidence line is lost.
- A dry run over a fixture findings file prints a tree and creates nothing, asserted by the absence of any network call in the pure path rather than by observation.
- The six gates, and `pyproject.toml`'s `known_first_party` gains the module so `deptry` does not read its sibling imports as missing dependencies.

## What the first review round changed, and why it is in the spec rather than only in the diff

A reader that had not seen the implementation found the design's load-bearing assumption to be false, which is worth recording here because the assumption is the kind a later reader would make again.

**The sweep could not produce the input this design requires.** The fan-out brief tells each domain subagent to return its matrix capped to the significant rows, and the consolidation step tells the front door not to recount those rows because they are capped. So the front door never held an uncapped set, and the findings file specified above was unproducible: the emitter would have emitted exactly the issue set missing the capped rows, under a guarantee saying it did not. Deciding the input contract without checking that the producer can meet it is the error, and the repair is in the producer: the brief now asks for the full findings list as data beside the capped matrix, and consolidation keeps it concatenated and untouched.

**Three consequences followed from the same review.**

- The report template offers "File issues (Important+)", and the emitter had no severity filter, so the report named a next step its own tool could not perform. The emitter takes a floor now, defaulting to no floor, because dropping findings is a decision the caller states rather than one the tool assumes.
- The consolidation rule requires a caveat to travel with an identifier the sweep could not confirm. Prose beside a number carries that; a machine-read format does not, so a finding carries its caveat in a field.
- The JSON needed a destination and has no question of its own, because the front door's format question is already at the four-option cap. It is derived from the report's path instead, and a run that writes no report writes no JSON - which means an unattended sweep with no stated destination cannot feed the emitter at all. That is the right outcome rather than a gap: a run nobody asked for a destination from is not the one that should file issues in somebody else's tracker.

**The labels are the emitter's own vocabulary** - `audit:<domain>` and `priority:urgent` / `priority:normal` / `priority:low` - and nothing in this repository fixed a vocabulary for an audit issue set before now. They are written down in the front door's step 4 because `--create` would create them in a repository this project does not own, and a target with its own priority names would end up carrying two sets.
