# The tool's registry chooses the one-shot runner, not the partition's package manager

Issue #42. `audit/SKILL.md`'s runner table promises `yarn dlx <tool>` for yarn, and Yarn classic has no `dlx`.

**Status.** Written and self-approved under autonomous mode, with no maintainer review gate. Every decision below records the alternative it rejected and the source that settled it, so any one of them can be reopened on evidence rather than on recollection. The gate that was not granted is the review of the resulting PR.

## The decision, and why it was narrower than the issue thought

#42 frames this as a design question it owns, with two ways out:

1. a registry package need not be fetched by the partition's own package manager, so a Yarn 1 partition uses `npx`; or
2. the partition's own runner is required, so Yarn 1 has no one-shot form and the table routes to `## Tooling fallback`.

**Option 1, and the deciding argument is not the one the issue gives.** The issue argues on the merits - nothing about fetching `dependency-cruiser` resolves from the target's lockfile, so any runner satisfies the constraint the table exists to serve. That is right and it is not what settles it. What settles it is that the same question has already been answered for #77, recorded on the loop's ledger: *"the registry becomes a field ... the runner comes from the tool's registry, not from the partition's language."* Option 2 makes the runner a property of the partition, which is that decision inverted. Taking it here would leave two parts of the same family disagreeing and would have to be undone when #77 lands.

So this is implementing a settled decision one issue earlier rather than making a new one. If the reading is wrong, reversing it means reopening #77's decision too, not just this change.

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
| **`npx` ships with npm "since 5.2"** | not in npm's own `npx` page | **Not adopted.** #42 states it; npm's page dates the change to v7 and says nothing about 5.2. The durable claim is that `npx` ships with npm, so that is what gets written |
| **A `packageManager` field in `package.json` separates the yarn majors** | not in the migration guide | **Not adopted.** #42 already marked it unverified and it stays unverified rather than being promoted by being repeated |

The prior in-repo statement of the first fact, in `2026-08-11-arch-dlx-runner-forms-design.md`, says Yarn classic's list "carries 43 commands". The index read today lists more than that. The number is not the claim and is not restated anywhere in this change: `dlx` being absent is a structural fact, a count is a snapshot, and CLAUDE.md forbids asserting one that was not computed.

## Version detection is not required, which is the point worth keeping

The issue's third acceptance criterion is conditional: the inventory records the Yarn 1 / Modern distinction *if the fix depends on it*. Under option 1 it does not. `npx` is correct on either yarn, so an agent never has to know which it is in order to run a registry package.

That is deliberately better than making the inventory carry a version. The inventory records package managers and lockfiles rather than versions, so requiring a version here would either expand the inventory contract or leave an agent inferring one - and an agent that guesses Modern on a classic partition lands exactly back in this bug. A rule that is correct without the distinction has no such failure mode.

The distinction still has a use - preferring `yarn dlx` where it exists - so the verified signal is stated for whoever wants that preference, without any instruction depending on it.

## The records need no edit, and that is a finding rather than an assumption

Computed over every route in the tree: each route whose `argv_by_partition` carries a `yarn` entry spelling `dlx` also carries a shared `argv` beginning `npx`. Those are `arch/coupling`, `arch/cycles`, `arch/layering` and `arch/over-decomposition`'s `dependency-cruiser` routes, and `test/mutation`'s `@stryker-mutator/core` route.

So the shared rule reaches them: a `yarn`-keyed `dlx` entry is Yarn Modern's form, and the route's shared `argv` is what a classic partition runs. Every affected route already has that fallback in place, so #42's fifth criterion is met by the rule rather than by five record edits - which is the same conclusion `2026-08-11-arch-dlx-runner-forms-design.md` reached when it deferred this: "one defect in one shared sentence rather than four in the records".

The other `dlx` occurrences in the tree are `disposition: forbidden` routes carrying a bare `dlx depcruise` or `dlx cyclonedx-npm`. Those are dependency-confusion warnings rather than runner forms, and nothing here touches them.

## What changes

One paragraph of `audit/SKILL.md`, in three places within it:

- The runner list stops presenting itself as a per-manager table and states the rule instead: the runner must reach the tool's registry, the partition's own manager is a preference rather than a requirement, and Yarn classic's absent `dlx` is named with `npx` as its route.
- The escape clause, which today reads "For a package manager not listed, use its documented one-shot form", is widened. Its premise is the bug #42 identified: yarn *is* listed, so an agent with a broken form never reaches the hatch. It now covers a listed manager whose named form does not exist as well as an unlisted one.
- The registry-package clause's condition "as long as the registry it comes from is the one the partition's runner reaches" becomes a condition on the runner chosen rather than on the partition, since choosing a different runner is now the sanctioned move.

## What this does not do

- **It does not change the taxonomy's three kinds**, and it does not touch the mandatory manager-matching for a package-manager subcommand. `yarn licenses list` on a pnpm partition is still wrong for the reason the paragraph already gives.
- **It does not add a `registry:` field.** That is #77, already decided; this change is the prose rule that field will later make machine-readable, and it is deliberately written so #77 narrows it rather than contradicting it.
- **It does not expand the inventory contract** to carry package-manager versions, for the reason above.
- **It does not edit any check record**, and it does not renumber or recount anything in `2026-08-11-arch-dlx-runner-forms-design.md`, which is a historical record.

## Verification

`docs/audit/sweep-obligations.md` is checked because the change edits `audit/SKILL.md`. One row covers this bullet, quoting `Run the domain's detection/measurement tooling here` and dispositioning it `restated`; its disposition text summarises the bullet as covering "the one-shot runner per package manager", which is the phrase this change makes wrong, so that row's wording is updated with it. `tests/test_sweep_obligations.py` holds the anchor and the quotation, neither of which moves.

Then the four gates, and a stale-prose pass by an agent that has not seen the change, scoped by blast radius over `dlx`, `npx`, `one-shot`, and the runner-table wording wherever it is described rather than only where it is quoted.
