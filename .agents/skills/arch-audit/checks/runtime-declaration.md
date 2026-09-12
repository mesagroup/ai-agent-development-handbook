---
id: arch/runtime-declaration
domain: arch
locality: global
evidence: >-
  Two lists and the difference in one direction. Each detected runtime is
  evidenced by the manifest that makes it one, at `file:line`; each declared
  runtime by the line of the binding-rules file naming it. A row records the
  detected runtimes the declaration does not name, and, where a declaration is
  present but thin, which of the two required clauses it is missing. It records
  the file it resolved as the binding-rules file either way, since the
  comparison is unreadable without it.
handbook:
  - codebase-structure/count-the-runtimes-and-make-each-one-earn-its-place-b
routes:
  - lang: any
    kind: procedure
    note: >-
      Two reads and a set difference, with nothing installed. **Detected
      runtimes** come from the partitioning `audit-core` step 1 already did:
      a language counts as a runtime where it carries its own dependency
      manifest - `pyproject.toml`, `requirements.txt`, `package.json`,
      `go.mod`, `Cargo.toml`, `Gemfile`, `pom.xml`, or a `Dockerfile` line
      that installs that language's packages, which is a dependency
      declaration with nothing locking it. A base image alone is not one.
      **Declared runtimes** come from the
      binding-rules file's own list. **The finding is the difference**, plus
      a declared non-primary runtime missing what it buys or who maintains
      it. Record the manifest path for each detected runtime and the line for
      each declared one, so the difference is checkable rather than asserted.
    alone_insufficient: >-
      A language named somewhere in the rules file is not a declaration. The
      clause asks for a list that marks its primary and justifies each of the
      others, so a passing mention - a build command that happens to name
      `npm`, a prose aside about a script - does not satisfy it, and reading
      the surrounding lines is what tells the two apart. Read before reporting
      a runtime as declared; the mechanical half only finds candidates.
---

# Runtime declaration

Whether the project's binding-rules file **names every runtime the project carries**, marks which one is primary, and for each of the others says what it buys and who maintains it. The finding is the set difference between the runtimes a snapshot detects and the runtimes that list declares. What this prevents is not a second stack, it is an *unowned* one: a service or a function in another language, with a dependency file nobody locked, no test command anyone runs and no CI lane, which stays invisible until it breaks or a vulnerability lands in it.

## Which file, which runtimes, and what counts as one

**The binding-rules file is resolved by role, not by path.** The handbook defines it under `Where the binding rules live` in Part 0 as the file a team and its coding agents both read as authoritative, and deliberately does not name it - it is `CLAUDE.md` in one project and `AGENTS.md`, `CONTRIBUTING.md` or a file under `docs/` in another. Resolve it by asking which file the project treats as binding, and say in the row which file you resolved it to, because a reader cannot check the finding without knowing what was read. This record is where the family states that resolution, and `arch/import-rule-declaration` reuses it rather than writing a second one, so a change to it changes both checks.

**A dependency manifest is what makes a language a runtime.** A single `.py` script in a TypeScript repository, with no dependency declaration of its own, is a file in another language and not a second stack; the same script beside its own `requirements.txt` is. The manifest is the discriminator because it is what brings the costs the clause is about - a graph to lock, a surface to scan, a cadence to schedule - and a language with none of those brings none of them.

**A `Dockerfile` counts where it makes the declaration, not where its base image carries an interpreter.** A line installing that language's packages is a dependency declaration in its worst form - a surface with nothing locking it - so it makes the language a runtime exactly as a manifest does. `FROM python:3.12` on its own does not: a base image is as often the primary stack's own delivery vehicle as it is a second stack's, so it cannot tell those apart, and a script it runs that needs nothing installed carries none of the costs the rule above is about. Stated because the two readings disagree on the same tree - a repository whose only manifest is a `package.json`, with a Dockerfile built on a Python image and one dependency-free `.py` file, is one runtime and not two.

**The check counts runtimes, not dependency surfaces.** Two Python footprints with their own dependency files are one runtime and two surfaces, and whether each surface is locked and scanned belongs to `deps`. But an undeclared runtime's row lists **every** footprint that evidences it, because the clause says a stack arriving as several separate footprints, none of them named, is that failure repeated rather than one instance of it - so the count of findings is per runtime and the extent within one is carried by its evidence.

**No binding-rules file, or one with no runtime list, is a finding and not a clean result.** It is the state in which every detected runtime is undeclared, so it reports as such - one row per detected runtime, naming the absence as the reason the declaration was not found. A check that reported "nothing to compare" here would return silence for the worst case it can meet.

## Severity

**Important** - a runtime present in the tree and absent from the declaration. This is the clause's own failure and the whole of the check's subject: the runtime is unowned, and nobody has said what it buys or who carries it.

**Minor** - a non-primary runtime that is declared but thin: named in the list, with what it buys or who maintains it missing. The stack is owned; the record of why is incomplete. A missing primary marking is this tier too, because a list that marks no primary makes every entry read as needing the justification half.

There is deliberately **no Critical tier**. The tiers here run out at Important because the check asks whether a runtime is declared and never whether it should exist, so it has no attacker path and no evaded gate to offer - those belong to the domains named below.

**A runtime declared but not present has no tier, and that is the whole of its treatment.** The clause requires the declaration to cover what the project carries; it says nothing about an entry for a stack that has since gone, and this check reports only the difference in the direction the clause names. A stale entry is a documentation-accuracy question and belongs to Part 8 with the rest of them. So the comparison runs one way: detected minus declared. Reporting the other way would be this check deciding the list should be shorter, which is a stack judgment wearing a declaration check's clothes.

## Fix

Add the missing runtime to the binding-rules file's list, mark which runtime is primary, and for each non-primary entry write the two things the clause asks for: **what it buys** - the library, platform requirement or constraint that the primary stack genuinely could not meet - and **who maintains it**, named as a person or a team rather than left to the reader.

Where the answer to "what it buys" turns out to be nothing, that is a stack decision and not a documentation one: it belongs to the project's own judgment about which runtimes to carry, which this check does not make.

## What this check does not do

**It does not rate the stack.** The finding is "this runtime is present and unnamed", never "this runtime should not exist". Whether a second stack could be replaced by the primary one turns on which libraries exist and who the team can staff, neither of which is in a snapshot - which is why the handbook splits that half off as process and why an `arch/guest-stack` check was considered and rejected.

**It does not re-raise a cost another domain owns.** An undeclared runtime usually brings untested code, a stack CI never exercises, an unlocked dependency file and a second unscanned vulnerability surface. Those are `test`'s, `ci`'s and `deps`'s respectively, and each already has a check for it. Reporting them here would double count the findings the front door exists to consolidate, which is the first reason the guest-stack check was rejected and applies to any check asking whether the stack is good rather than whether it is declared.

## Review lens

**Declaration completeness** - does the rules file now name every runtime a fresh detection pass finds, mark exactly one primary, and carry both required clauses for each of the others; and was a runtime added to the list rather than removed from the tree to close the finding, which would be a stack decision arriving as a documentation fix?

**No double counting** - did the fix stay inside the declaration, leaving the undeclared runtime's testing, CI and dependency costs to the domains that own them, rather than resolving them here where nothing tracks them?
