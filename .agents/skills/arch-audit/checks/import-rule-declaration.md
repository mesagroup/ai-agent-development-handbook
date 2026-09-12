---
id: arch/import-rule-declaration
domain: arch
locality: global
evidence: >-
  One row for the project, because the rule is one declaration the project
  either made or did not. The row names every home that was read and what each
  held, in the absent case as much as the present one - the file resolved as
  the binding-rules file, and each contract config looked for by name - since
  "the rule is not written down" cannot be checked without knowing where the
  search went. Where a rule is present, the row cites it at `file:line` and
  records which tiers it names, so a reader can see whether it constrains the
  tiers the tree actually has. Where the tree has one tier and nothing to
  constrain, the row records that and the inferred tier list it was read
  against, because that is what turns a clean result into a checkable one.
handbook:
  - codebase-structure/point-every-dependency-toward-the-core-and-never-cycle-b
routes:
  - lang: any
    kind: procedure
    note: >-
      The binding-rules file, whatever the partition's language. Resolve it the
      way `arch/runtime-declaration` does and do not invent a second rule: that
      record resolves it **by role rather than by path**, because the handbook
      defines it as the file a team and its coding agents both read as
      authoritative and deliberately does not name it - `CLAUDE.md` in one
      project, `AGENTS.md`, `CONTRIBUTING.md` or a file under `docs/` in
      another. Read it for a statement of **which tier may import which**, in
      whatever words the project uses - "A may import B, never the reverse",
      an ordered list of layers with a direction, a table of allowed edges.
      Say in the row which file you resolved, because the finding is
      unreadable without it. A tier list with no direction is not this rule: it
      says what the tiers are and not what may import what, which is the half
      the clause asks for.
    alone_insufficient: >-
      An absent statement here is not the finding on its own. A project may
      have written the rule as an executable contract instead, which the
      language routes read, and that is the stronger form rather than a
      weaker one.
  - lang: python
    kind: procedure
    note: >-
      The executable contracts a Python project writes this rule as, read as
      configuration rather than run. `import-linter` keeps its contracts in
      `.importlinter`, or in `setup.cfg` or `tox.ini`, and `tach` keeps its
      module boundaries in `tach.toml` or under `[tool.tach]` in
      `pyproject.toml`. A contract naming the layers and their permitted
      direction **is** the rule written down, in the strongest form the clause
      asks for - it says the clause wants the rule recorded *so that* a linter
      can enforce it, so a project that went straight to the linter has
      satisfied it without a prose sentence anywhere. Neither tool is run
      here and no command is prescribed for either: whether the code obeys the
      contract is `arch/layering`'s question and that record already
      prescribes both tools for it.
    alone_insufficient: >-
      An absent contract is not the finding on its own either, for the mirror
      of the reason above: the rule may be stated in the binding-rules file,
      which the `lang: any` route reads.
  - lang: typescript
    kind: procedure
    note: >-
      The same reading on the TypeScript side, and the one place a project can
      look compliant while having declared nothing. A `.dependency-cruiser`
      config whose rules name forbidden edges between directories is the rule
      written down. `tsconfig` path aliases and project references are
      **not**: they say which names resolve where, and a project can carry a
      full set of aliases while permitting every tier to import every other,
      so reading them as a declaration is how this check passes a project that
      never made one. `arch/layering` does read those aliases as the declared
      boundaries where no config exists, which is the right fallback for
      judging edges against *something* - and it is exactly the substitution
      this check must not make, because the question here is whether the
      project stated a rule rather than whether the audit can find a rubric.
    alone_insufficient: >-
      An absent config is not the finding on its own, for the same reason as
      the Python route: the rule may be in the binding-rules file.
---

# Import rule declaration

Whether the project has **written down which tier may import which** - in its binding-rules file, or as a layering-contract config a linter reads. The finding is that no such statement exists, and it is a declaration finding: this check never asks whether the rule is a good one, and never whether the code obeys it.

What it prevents is the domain judging a project against an architecture the audit supplied. `arch-audit`'s setup step reads the contributor guide for a stated tier structure and, where none is documented, **infers** the layers from the directory structure and confirms them with the user before flagging anything. That is the right handling - a domain with no rubric can do nothing else - but it consumes the absence as a branch in the setup, so it never reaches the report. A project that has never written its import rule down therefore passes this claim while `arch/layering` grades it against inferred tiers. **The setup step handles the absence; this check reports it.** Those are two jobs, not two policies.

## What counts as written down

**Either form satisfies the clause, and the contract is the stronger one.** The clause asks for the rule to be recorded *so that* an import-boundary linter can enforce it, so a project whose rule exists only as an `import-linter` contract has met it more completely than one with a sentence in `CLAUDE.md` and no config. Read every home before concluding anything: each route's `alone_insufficient` says so, because an absence found in one place is not the finding.

**A direction is what makes it the rule.** "The tiers are `core`, `services`, `apps`" names the tiers and permits everything; the clause asks which tier may import which. A list without a direction is not a declaration of this rule, and reporting it as one passes the project on the half it did not write.

**`tsconfig` path aliases are not a declaration**, and this is the substitution most likely to be made, because `arch/layering` deliberately does read them as the declared boundaries when nothing else exists. That is the right fallback for *judging edges*, and the wrong answer here: aliases say which names resolve where, and a project can carry a complete set of them while every tier imports every other.

## A single-tier project is not a finding

The rule constrains imports **between** tiers, so a tree with one tier has nothing to constrain and satisfies the claim vacuously. Report the domain's own clean value with the row naming the tier list it was read against - not `not-applicable`, which `audit-core` reserves for a check with no lens in the partition's languages, and this check has one in every language it looks at.

This is the one place the check depends on the setup step it otherwise reports around: whether the tree has tiers to constrain is the setup's inferred layer list, and the row cites that list so a clean result is checkable rather than asserted.

## The two neighbours, and where each line falls

**`arch/layering` asks whether the code obeys the rule.** It takes the documented - or inferred and confirmed - rules as a rubric it is handed, and reports the edges that break them. It is silent on a project that documented nothing, because the rubric it was handed came from the audit. This check is the one that reports that.

**`ci/gate-enforcement` asks whether the contract can block.** Its subject is whether intended gates are run and *required*, so a layering contract that exists and is not wired into a required job is a `ci` finding and a pass here. The row this record closes already cites that check and keeps it: the two answer different halves of the same sentence, the declaration and the enforcement.

## Severity

**Minor** - no tier-import rule is written down, in any of the homes above, on a project whose tree has tiers to constrain. It is Minor and not higher because the clause's own cost is indirect: nothing is broken by the absence, and what it buys is the ability to enforce mechanically what is currently held in memory.

There is deliberately **no Important or Critical tier**. This check asks whether a declaration exists and never what the rule says or whether the code follows it, so it has no violated boundary and no evaded gate to offer - those are `arch/layering`'s and `ci/gate-enforcement`'s, and each already has them. A row here that reached for a higher tier would be borrowing severity from a finding it did not make.

## Fix

Write the rule in the binding-rules file: name the tiers and state the permitted direction between them, in whatever form the project's own document uses.

Then encode it where a linter reads it - an `import-linter` contract, a `tach` boundary set, a `dependency-cruiser` rule, or the detected language's equivalent - because that is what the clause means by enforceable rather than remembered. Wiring that config into a required CI job is `ci/gate-enforcement`'s finding to close rather than this one's, and worth doing in the same change.

**Two closes are wrong, and detection cannot tell either from the right one.** A rule written permissively enough to forbid nothing satisfies every mechanical reading of this check - a statement exists, in the right file, naming the tiers - and declares no constraint at all. So does collapsing the tree to one tier, which makes the check vacuous by the rule above rather than satisfied. Both close the finding and leave the project where it started, which is why the gate here is a read of the change rather than a re-run of the detection.

## What this check does not do

**It does not rate the rule.** The finding is "the rule is not written down", never "these tiers are wrong" or "this direction is backwards". A project that declares an unusual layering conforms; deciding whether its tiers are ordered well is a judgment no snapshot settles, and the handbook keeps that half as process for that reason.

**It does not read the code.** No route runs a tool, and none needs the dependency graph: the declaration is in a document or a config file, both of which are in a read-only clone. The graph belongs to the checks that judge edges.

## Review lens

**Declaration, not conformance** - does the row say whether a rule was written down, and not whether the imports follow it? A row whose evidence is a violating edge is this check answering `arch/layering`'s question.

**Every home named** - does the row name the file resolved as the binding-rules file and each contract config searched for, including the ones that held nothing? An absence with no search behind it cannot be checked.

**The rule constrains something** - does the written rule forbid at least one edge the tree could contain, and were the tiers it names the tiers the project has? A permissive rule and a collapsed tier list both close this finding while declaring nothing, and telling them from a real fix is a read of the change rather than a re-run.
