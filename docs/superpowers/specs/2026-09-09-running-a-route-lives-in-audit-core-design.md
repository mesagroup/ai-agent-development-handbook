# Running a route is engine doctrine, so it lives in `audit-core`

Issue #70. `audit/SKILL.md` tells an executing agent how to turn a route into a command line; `audit-core/SKILL.md` describes the record schema and never describes running one. A domain skill invoked directly - the path `audit/SKILL.md` itself recommends for a deep single-domain run - reads its own `SKILL.md` and `audit-core`, and neither says what to run.

**Status.** Written and self-approved under autonomous mode, with no maintainer review gate. Every decision below records the alternative it rejected and how it was settled, so any one of them can be reopened on evidence rather than on recollection. The gate that was not granted is the review of the resulting PR.

## Where the instruction goes, which was already decided

#70's body offers three homes and calls the choice doctrine rather than wording: once in `audit-core/SKILL.md`, nine copies in the domain skills, or a reference from each domain skill into `audit/SKILL.md`. The nightshift ledger, issue #78, records the maintainer's decision under `## Decisions already taken`: **`audit-core/SKILL.md`, once, with `audit/SKILL.md` referencing it rather than keeping a second copy.** Rejected there: nine per-domain copies, which is what the record schema exists to avoid, and pointing at `audit/SKILL.md`, which makes the sweep front door a dependency of the path that exists to bypass it.

This is implementing that decision rather than making it. Two things it leaves open are settled below, and the tick that implemented it posted both to #70 so the tracker carries them rather than only the ledger - which is the lesson the previous tick recorded after citing a ledger-only decision as settled.

## The nine domain skills need no edit, which is the decision paying off

Checked rather than assumed, across all nine: each opens by naming `audit-core` as the skill it specializes and saying to read it first, because it owns the loop and the cross-cutting rules. So a section added to `audit-core/SKILL.md` is reached by a direct invocation of any domain skill with no per-domain pointer, and the "nine copies to keep in step" option is not merely worse - it is unnecessary.

That is worth stating because #78's queue table lists nine domain skills in this item's `touches` column. They are not touched.

## The first open question: does the one-shot runner rule come with the route contract?

#70's body enumerates the route contract - which `kind` hands you a command, what each `disposition` means, how `argv` and `argv_by_partition` relate, that a `then` is a second command and `own_runner` says to put no runner in front - and that is one paragraph of `audit/SKILL.md`. It does not say whether the *runner* rule travels with it. The question matters twice over: `own_runner`'s entire meaning is "put no runner in front", which negates a rule `audit-core` does not state, and a route's `argv` is written as the tool's own command line rather than as a runner's.

**Settled by computation over the tree rather than by reading.** Counting each `command` route's shared `argv` and each per-partition override separately, and excluding whatever `own_runner` covers: 34 command forms are written as a bare tool invocation - `pytest --cov-branch --cov-report=term-missing`, `pip-audit -r requirements.txt`, `cyclonedx-py requirements`, `mutmut run` - against exactly one form that carries `own_runner`, `deps/inventory`'s `uv export` on the uv partition. So an agent that loads a domain skill directly cannot turn 34 of the tree's prescribed commands into a command line without knowing that a one-shot runner goes in front. The rule travels.

The previous tick found an instance of the same gap from the other direction: `test-audit/checks/mutation.md`'s note was the only runner instruction a directly-invoked `test-audit` would ever read, because `audit-core` carries none. That is this issue's premise met in the wild, and it is why the runner rule is part of the answer rather than a separate issue.

## The second open question: `audit/SKILL.md` keeps its own runner paragraph, and that is not a second copy of the thing being relocated

The relocated route contract leaves `audit/SKILL.md` with a reference. Its *runner* paragraph stays where it is, so that rule ends up stated in both files, and #70's second acceptance criterion asks for exactly one copy or a stated reason why more than one is right. The reason:

- **`docs/audit/sweep-obligations.md` is the repository's own answer to this question, and its answer is `restated`.** That ledger exists because the sweep "substitutes its own steps for the `audit-core` loop rather than running it, so it inherits none of that step implicitly", and most of its rows are `restated` - the sweep carrying the same rule in its own words. A second voice is the normal disposition there, not the exception, and its `delegated` disposition is reserved for a rule the sweep must *not* restate because doing so would give a domain agent two authorities for one rule.
- **The two halves fall on opposite sides of that line.** The route contract is a field-by-field description of frontmatter that `scripts/audit_checks.py` validates, so a second prose copy is one more thing to keep in step with the loader, and a drift between them is a contract disagreeing with itself. That is `delegated`. The runner rule names no field; the sweep's copy says the same thing at the level of a target's partitions and package managers, which is detail the sweep has because it built the project inventory and a domain agent reading `audit-core` alone does not. That is `restated`.
- **Not editing the sweep's runner paragraph also keeps this change out of the way of an open PR.** PR #42/#80 rewrote that exact paragraph and verified its facts against Yarn's and npm's own documentation. Relocating it here would delete those sentences on this branch and require them to be reconstructed at merge, which is a way to lose a verified fix.

So `audit-core`'s runner statement is **registry-neutral**: it names `uvx` and `uv run --with` for a PyPI package and `npx` for an npm one, states that the runner has to reach the registry the tool is published in, and names no `dlx` form and no package-manager-specific one-shot at all. A rule that never mentions yarn cannot promise a command Yarn classic does not have, and one that does not restate #80's carve-out does not inherit #80's review.

That the registry rather than the partition chooses the runner is not taken from #80. `audit/SKILL.md` on `main` already states it for the cross-language case, in the sentence saying a route's `lang` names which of the target's languages the route applies to rather than which registry its tool is published in, with `test/new-code-coverage`'s `diff-cover` as the worked example and the unrelated npm package of the same name as the hazard. What goes into `audit-core` is that sentence's doctrine, which is on `main` today.

## What changes

**`audit-core/SKILL.md` gains one section, `## Running a route`**, between the loop and the authoring guidance, because it is run-time instruction rather than either a loop step or an authoring rule, and step 1's detection-tooling sentence points at it.

It carries two things:

- **The runner and kinds doctrine**, in the registry-neutral form above: a fetched tool runs through a one-shot runner reaching its own registry, the runner reaches only one of the three kinds of thing a record names, a package the audit must *import* rather than execute is not served by a runner at all, a package-manager subcommand runs only where that manager is the partition's own, a standalone binary is available or it is not, prefer what the inventory reports already installed, and record the resolved version of anything fetched.
- **The route contract, relocated from `audit/SKILL.md` essentially verbatim.** Three references are repointed, because each named its old surroundings: "the one-shot runner this bullet otherwise requires" now names the rule above it in the same section, and the two sentences deferring to `ungranted_note`'s scoping "above" now name step 1, which is where `audit-core` states it. Nothing else in that paragraph's wording moves, so the diff reads as a relocation and a reviewer can check it as one.

**`audit/SKILL.md`'s routes bullet becomes a reference** to that section, keeping its own first sentence - which schema a record declares and that either can appear - because choosing what to tell a dispatched agent is the sweep's own concern, and dropping the field-by-field contract that follows it.

**`docs/audit/sweep-obligations.md` gains one row per obligation the new section states**, since its rule is that every sentence of `audit-core` telling a run to do something has a row. The route-contract rows are `delegated`, in that disposition's own words: the sweep must not restate them, because restating them would give a domain agent two authorities for one rule. The runner rows are `restated`, against the sweep's own runner paragraph.

One existing row moves with it. The row anchored on `Run the domain's detection/measurement tooling here` justifies the sweep's length by saying it "adds a constraint the engine does not carry: the tooling must run without adding a dependency to the target". After this change the engine does carry it, so the clause is false and the row says instead that the sweep restates at partition level what the engine states registry-neutrally.

## What this does not do

- **It does not touch the sweep's runner paragraph**, for the reasons above, and so it does not renumber, reword or relocate anything PR #80 changed there.
- **It does not change the record schema**, the two mutually exclusive schemas, or anything the loader validates. No check record is edited and no test in `tests/scripts/` changes behaviour.
- **It does not add a `## Running a route` copy to any domain skill.**
- **It does not restate the grants and tiers doctrine.** `audit-core` step 1 already carries it at length, including the two ways a migrated record's projected `tooling`/`needs` pair over-reports tiering, so the new section defers to step 1 rather than repeating it.

## This branch conflicts with PR #80, deliberately and recoverably

Both branches were cut from `main` and neither is based on the other. They collide in two places, and the resolution is deterministic rather than a judgement call:

- **`audit/SKILL.md`'s routes bullet.** #80 inserted a sentence into it - that a partition key names a package manager rather than a version of one, so a keyed entry can spell a subcommand this partition's manager does not have - with the `yarn` case as its worked example. This branch deletes the bullet's contract half. Git will present it as deleted-versus-modified. The resolution is to take the deletion and paste #80's sentences into the relocated contract in `audit-core/SKILL.md`, at the same position they occupied: immediately after the sentence about `argv` and the matching `argv_by_partition` entry.
- **The detection-tooling row of `docs/audit/sweep-obligations.md`.** Both branches reword the same cell for unrelated reasons: #80 because the runner is chosen by registry rather than by package manager, this branch because the engine now carries the rule. Both statements are true together and the merged cell says both.

Merging #80 first and rebasing this branch is the order #78's queue already prescribes.

## Verification

The four gates, plus `tests/test_sweep_obligations.py`, which is the one that can actually fail on this change: every new row's anchor must occur in `audit-core/SKILL.md` exactly once, every row must carry a disposition from the ledger's own vocabulary and a justification, and no table row may fall outside the parser's reach.

Then a stale-prose pass by an agent that has not seen the change, scoped by which sentence carries the decision rather than by the words this change uses - the previous tick's lesson, and here the sentences at risk are the ones that tell an agent where to read the route contract: the domain skills' opening paragraphs, `audit/SKILL.md`'s remaining routes bullet and its detection-tooling bullet, and `CLAUDE.md`'s account of what each file owns.
