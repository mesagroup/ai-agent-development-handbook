# Goal

What this repository exists to deliver, stated once so that every issue can say which part of it the issue serves. The tracker is held against this document: an issue's `Serves:` line names an outcome below, a queue is composed in the order of the outcomes, and work in a "does not count" category is not opened as an issue without a reason recorded against this file.

## Deliverable

A productionization gap-assessment of an external agentic codebase against the engineering handbook in [`engineering/`](engineering/README.md), produced by running the audit skill family in [`.agents/skills/`](../.agents/skills) against that codebase as a Claude Code plugin. Two artifacts per audited repository: a **prose report**, ordered by area and priority, in two registers - *defects* (fix what exists: security, data exposure, unpinned dependencies) and *absences* (a phased adoption roadmap of the handbook's lifecycle) - and an **importable issue set**: one top-level epic, per-area child epics, findings clustered into labelled sub-issues, each body carrying `file:line` evidence and a handbook citation. The first recipients are two TypeScript document-management targets in one organisation: `<polyglot-monorepo-target>`, a pnpm and turbo monorepo of independently deployed services, and `<single-package-target>`, a Next.js application calling the provider SDK directly. The real names live in the engagement's own records, never in this repository.

## Outcomes

In order. The first is the one the deliverable is most blocked on.

- **O1 - The sweep gives an honest per-check status on the targets' actual shapes.** Reached when a full `/audit` run over `<polyglot-monorepo-target>` yields a findings matrix in which every check lands as `ok`, a finding, `not-applicable`, or `no-evidence` with its reason; every whole-graph metric states the scope, service or repository, it was computed over; and no check whose tools answer different halves reports `ok` with one half unobtained. First because a wrong number in a client report is worse than a missing section.
- **O2 - Every handbook part the report must speak to has a lens or a stated report-only disposition.** Reached when the severity by coverage cross-tab in [`audit/handbook-traceability.md`](audit/handbook-traceability.md) shows no critical row unmapped, and each remaining lens the epic planned has either shipped as check records carrying a `handbook:` citation or been declined in the matrix with a `report-only` note saying why.
- **O3 - The issue set is produced by a script, not by hand.** Reached when `scripts/` holds an emitter that, given a findings matrix and a target repository, prints in dry-run mode the epic, child-epic and clustered sub-issue tree with severity, labels, `file:line` evidence and a handbook citation in each body, creates nothing without an explicit flag, and has unit tests over its pure logic.
- **O4 - The family has passed a gate run on a repository with a known baseline.** Reached when the full sweep has run against a repository whose earlier audit findings are on record, the diff against that record accounts for each finding as resolved, still open, or new, the emitter's dry-run output has been reviewed for shape, and every skill regression the run exposed is fixed or filed with a `Serves:` line.

## Does not count

Work this repository can absorb indefinitely and has decided not to. An item in one of these categories is written under `## Found, not fixed` in the pull request that found it, and becomes an issue only when the batch review returns `open` for it.

- **Verification-harness self-consistency beyond what a named target's package manager needs.** Guards that hold one internal table against another, where no partition an audit is about to meet exercises the difference.
- **Tooling coverage for package managers no named target uses.** Yarn Classic, Yarn Berry, bun, deno. Re-enters the moment such a target is named.
- **The engine's prose style and word count.** Settled by eval where it is settled at all, never by trimming to a number.
- **Handbook clauses motivated by this repository's own way of working rather than by a gap a target showed.** The handbook grows when a target's report needs a clause it cannot cite.
- **Repository housekeeping.** Conventions-file edits, dependency gates, run logs. Done inside the pull request that needs them, not as issues of their own.

## Done when

Both named targets have a delivered prose report and a reviewed dry-run issue set, and every regression in the family those two runs exposed is fixed or filed. The gate run of O4 is a milestone on the way, not the end.

## How the tracker uses this

- Every issue body carries `**Serves:** O<n>`. An issue that cannot name one is either a gap in this document or not work, and which of the two is the maintainer's call, recorded here.
- A queue for a batch of work - a nightshift, a sprint - is composed against the outcome order above, and at least four of every five items serve a named outcome.
- Something found while implementing goes under `## Found, not fixed` in the pull request body, one line each, and is triaged when the batch closes.
