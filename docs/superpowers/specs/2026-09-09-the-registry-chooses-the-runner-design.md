# The tool's registry chooses the one-shot runner, not the partition's package manager

Issue #42. `audit/SKILL.md`'s runner table promises `yarn dlx <tool>` for yarn, and Yarn classic has no `dlx`.

**Status.** Written and self-approved under autonomous mode, with no maintainer review gate. Every decision below records the alternative it rejected and the source that settled it, so any one of them can be reopened on evidence rather than on recollection. The gate that was not granted is the review of the resulting PR.

## The decision, and why it was narrower than the issue thought

#42 frames this as a design question it owns, with two ways out:

1. a registry package need not be fetched by the partition's own package manager, so a Yarn 1 partition uses `npx`; or
2. the partition's own runner is required, so Yarn 1 has no one-shot form and the table routes to `## Tooling fallback`.

**Option 1.** The issue argues it on the merits - nothing about fetching `dependency-cruiser` resolves from the target's lockfile, so any runner satisfies the constraint the table exists to serve - and that argument is sound and sufficient on its own.

It is reinforced by, and must not be confused with, a decision recorded elsewhere. #77 asks the same question for a `registry:` field, and the maintainer settled it in favour of the field, with the runner coming from the tool's registry rather than from the partition's language; that is written on the nightshift ledger, issue #78, under `## Decisions already taken`. **It is not written on #77**, whose own first acceptance criterion - "A decision on whether the registry becomes a field or a convention in the argv" - is still unticked, and whose body still presents the argv convention as possibly cheaper. So a reader who checks #77 sees an open question, and this spec should not claim otherwise. The decision has been recorded as a comment on #77 as part of this change, so the tracker stops disagreeing with the ledger.

What that reinforcement is worth: option 2 would make the runner a property of the partition, which is the ledger's decision inverted, so taking it would set two parts of the family against each other. But the merits argument stands without it, which is the honest way to hold this - **reversing option 1 does not require reopening #77; it requires answering #42's own argument.**

There is a third, weaker support already in the tree, and it is worth naming because it is verifiable rather than remembered: #77's own "Interim" paragraph records that `audit/SKILL.md` already says `lang` does not name the registry, and the paragraph this change edits already carried that sentence. The rule here generalises prose the file was already committed to.

## What the constraint actually is

The bullet's own words are "without adding a dependency to the target". Every one-shot runner satisfies that identically, because none of them writes to the target. Matching the partition's manager is load-bearing for exactly one of the three kinds in the same section's taxonomy: a *subcommand of the target's own package manager*, where the subcommand resolves from the lockfile of the manager that owns it, which the paragraph already says and which nothing here changes. For a *registry package* the manager is incidental and the registry is what matters.

That reframing is what makes Yarn classic a non-event rather than a hole: an npm-registry tool on a Yarn 1 partition is fetched with `npx`, the same registry reached by a runner that exists.

## Verified against the tools' own documentation

Because the change is a normative instruction, each fact is read off the vendor's documentation rather than inherited. Two inherited claims did not survive.

| Claim | Source | Result |
|---|---|---|
| Yarn classic documents no `dlx` | Yarn 1 CLI index, `classic.yarnpkg.com/en/docs/cli/` | Confirmed. `dlx` is absent from the command index |
| `yarn dlx` is Yarn 2+ | `yarnpkg.com/cli/dlx`, the Modern docs site | Confirmed, and it takes `-p` / `--package`, repeatable |
| Modern and classic are separable by config filename | Yarn migration guide, `yarnpkg.com/migration/guide` | Confirmed verbatim: Modern "now uses `.yarnrc.yml`. Any other file is now ignored - this includes `.npmrc`", where classic read `.yarnrc` and `.npmrc` |
| `npx` ships with npm | npm CLI docs for `npx` | Confirmed that it ships with npm, and that it "was rewritten in npm v7.0.0, and the standalone `npx` package deprecated at that time" |
| **`npx` ships with npm "since 5.2"** | not in npm's own `npx` page | **Version not adopted.** #42 states it; npm's page dates the rewrite to v7.0.0, when the standalone package was deprecated, and says nothing about 5.2. What the paragraph now says is the durable half - `npx` ships with npm - paired with an instruction to confirm it from the inventory's already-installed field rather than assume it |
| **A `packageManager` field in `package.json` separates the yarn majors** | not in the migration guide | **Not adopted.** #42 already marked it unverified and it stays unverified rather than being promoted by being repeated |

The prior in-repo statement of the first fact, in `2026-08-11-arch-dlx-runner-forms-design.md`, says Yarn classic's list "carries 43 commands". The index read today lists more than that. The number is not the claim and is not restated anywhere in this change: `dlx` being absent is a structural fact, a count is a snapshot, and CLAUDE.md forbids asserting one that was not computed.

## Version detection is not required, which is the point worth keeping

The issue's third acceptance criterion is conditional: the inventory records the Yarn 1 / Modern distinction *if the fix depends on it*. Under option 1 it does not. `npx` is correct on either yarn, so an agent never has to know which it is in order to run a registry package.

That is deliberately better than making the inventory carry a version. The inventory records package managers and lockfiles rather than versions, so requiring a version here would either expand the inventory contract or leave an agent inferring one - and an agent that guesses Modern on a classic partition lands exactly back in this bug. A rule that is correct without the distinction has no such failure mode.

The distinction still has a use - preferring `yarn dlx` where it exists - so the verified signal is stated for whoever wants that preference, without any instruction depending on it.

## The records' frontmatter needs no edit; one record's prose did

Computed over every route in the tree: each route whose `argv_by_partition` carries a `yarn` entry spelling `dlx` also carries a shared `argv` beginning `npx`. Those are `arch/coupling`, `arch/cycles`, `arch/layering` and `arch/over-decomposition`'s `dependency-cruiser` routes, and `test/mutation`'s `@stryker-mutator/core` route.

So the shared rule reaches their frontmatter: a `yarn`-keyed `dlx` entry is Yarn Modern's form, and the route's shared `argv` is what a classic partition runs. Every affected route already has that fallback in place, so no `argv_by_partition` map is rewritten - which is as far as `2026-08-11-arch-dlx-runner-forms-design.md`'s "one defect in one shared sentence rather than four in the records" actually reaches.

The other `dlx` occurrences in the tree are `disposition: forbidden` routes carrying a bare `dlx depcruise` or `dlx cyclonedx-npm`. Those are dependency-confusion warnings rather than runner forms, and nothing here touches them.

**That computation was over frontmatter, and #42's fifth criterion is about prose.** Corrected during implementation, by a stale-prose pass that had not seen the change: `test-audit/checks/mutation.md`'s note read "and on a yarn one as `yarn dlx -p ...`" with no qualification by major - the same sentence shape #42 was filed against, reproduced inside a record. So one record's prose did need editing, and the earlier claim that none did was true of the data and false of the criterion.

It is the more consequential half, for a reason the pass established rather than assumed: `audit-core/SKILL.md` carries no runner rule at all - the sweep obligations row says as much, calling the constraint one "the engine does not carry" - so an agent invoking `handbook-audit:test-audit` directly, which the `audit` skill's own description recommends for a deep single-domain run, never reads `audit/SKILL.md`. For that agent the record's note was the only instruction, and the fix to the shared sentence did not reach it. That path is #70's subject, and this is a concrete instance of why it is open.

The four `arch` graph records need no prose edit, checked rather than assumed: their notes say "the three differ structurally" and assign no spelling to a manager, so only their `yarn:` frontmatter key is reinterpreted, which the shared rule handles centrally.

## What changes

One paragraph of `audit/SKILL.md`, in three places within it:

- The runner list stops presenting itself as a per-manager table and states the rule instead: the runner must reach the tool's registry, the partition's own manager is a preference rather than a requirement, and Yarn classic's absent `dlx` is named with `npx` as its route.
- The escape clause, which today reads "For a package manager not listed, use its documented one-shot form", is widened. Its premise is the bug #42 identified: yarn *is* listed, so an agent with a broken form never reaches the hatch. It now covers a listed manager whose named form does not exist as well as an unlisted one.
- The registry-package clause's condition "as long as the registry it comes from is the one the partition's runner reaches" becomes a condition on the runner chosen rather than on the partition, since choosing a different runner is now the sanctioned move.
- The argv-selection bullet gains the carve-out at the point it picks a command. That bullet is what an agent reads with a route in hand, it contains none of this change's vocabulary, and read alone it still sent a Yarn classic partition to the `yarn` key - so stating the exception only in the runner paragraph left the operative instruction wrong.

Plus one record and two guards:

- `test-audit/checks/mutation.md`'s note is qualified by yarn major, for the reason in the section above.
- A new test holds the structural fact the rule depends on: every route offering a `dlx` form under a partition key whose manager may lack `dlx` carries a shared `argv`, and that shared `argv` is not itself `dlx`-led. The loader validates a keyed entry's shape, not whether the manager it names owns the command it spells, so nothing else held either half. It is scoped to the at-risk key rather than to any `dlx` entry, so deleting the `yarn` forms cannot leave it passing over the `pnpm` ones, and it asserts its own population is non-empty.
- `CLAUDE.md`'s `argv_by_partition` description gains the same exception, since it tells a record author the map holds "that partition's own command".

## What this does not do

- **It does not change the taxonomy's three kinds**, and it does not touch the mandatory manager-matching for a package-manager subcommand. `yarn licenses list` on a pnpm partition is still wrong for the reason the paragraph already gives.
- **It does not add a `registry:` field.** That is #77, already decided; this change is the prose rule that field will later make machine-readable, and it is deliberately written so #77 narrows it rather than contradicting it.
- **It does not expand the inventory contract** to carry package-manager versions, for the reason above.
- **It does not edit any check record**, and it does not renumber or recount anything in `2026-08-11-arch-dlx-runner-forms-design.md`, which is a historical record.

## Verification

`docs/audit/sweep-obligations.md` is checked because the change edits `audit/SKILL.md`. One row covers this bullet, quoting `Run the domain's detection/measurement tooling here` and dispositioning it `restated`; its disposition text summarises the bullet as covering "the one-shot runner per package manager", which is the phrase this change makes wrong, so that row's wording is updated with it. `tests/test_sweep_obligations.py` holds the anchor and the quotation, neither of which moves.

Then the four gates, the new guard, and a stale-prose pass by an agent that has not seen the change.

**One lesson from that pass, recorded because it cost a defect.** The brief scoped it by vocabulary - `dlx`, `npx`, `one-shot`, runner-table wording - and the argv-selection bullet contains none of those words while being the sentence that actually chooses the command. A code review found that independently. Scope a prose pass by *which sentence carries the decision*, not by which words the change happens to use; a rule stated in one paragraph and applied in another is exactly what a vocabulary-scoped grep cannot see.
