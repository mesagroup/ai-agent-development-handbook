# Concrete `dlx` forms for the four arch-audit `dependency-cruiser` records (#32)

Status: accepted. Successor to the same fix in `test-audit/checks/mutation.md` (#5, commit `32043c4`), which is the precedent this follows rather than a design to redo.

## Problem

Four `arch-audit` records - `layering`, `cycles`, `coupling`, `over-decomposition` - tell an agent to feed `dependency-cruiser` the TypeScript compiler through a one-shot runner, give the npm form concretely, and then wave at the other two package managers: `` (`npx -p typescript -p dependency-cruiser`, or the pnpm/yarn `dlx` equivalent) ``. Each record's own next clause says what skipping the co-package costs: `dependency-cruiser` "reports zero modules cruised at exit 0", which reads as a clean project rather than as nothing having been analysed. So on a pnpm or yarn partition the clause hands back the exact failure the pinned npm form exists to prevent.

The reconstruction is not merely left to the reader, it has **two** obvious wrong answers, and both fail at exit 0:

- `pnpm dlx dependency-cruiser` fetches the right package and drops `typescript`, which is the zero-modules-cruised false-clean the records already describe.
- `pnpm dlx depcruise` follows the tool's own documented command name, and npm carries a package by that name which is not the tool. It is a dependency-confusion placeholder whose bin prints a message and exits 0, so this too produces no output at exit 0 - the `cyclonedx-npm` hazard `CLAUDE.md` documents, reached by following the record correctly.

The two share an exit code and nothing else, so the records state them as separate failures.

## Decisions

### 1. Every form is concrete, and names the command as well as the packages

Each record gives all three runners in full, pinning the packages with the runner's documented package option and naming `depcruise` as the command. The current parenthetical names no command at all, so it is a fetch rather than an invocation - and the command name is where the second hazard lives, which makes leaving it out the more expensive of the two omissions.

Forms, matching `test-audit/checks/mutation.md` so the family states one shape:

- `npx --package typescript --package dependency-cruiser -- depcruise <args>`
- `pnpm dlx --package=typescript --package=dependency-cruiser depcruise <args>`
- `yarn dlx -p typescript -p dependency-cruiser depcruise <args>`

The npm form moves from `-p` to `--package`. The shorthand was never verified against `npx --help`; the long option is what the row in `2026-08-10-typescript-test-security-lens-design.md` verified, and the switch costs nothing.

### 2. Pin the package rather than rely on the bin alias

`dependency-cruiser` publishes a `dependency-cruiser` bin alongside `depcruise`, so a bare fetch under the package's own name would also resolve the real tool. The records do not use it: `--package` is needed anyway to carry `typescript`, one mechanism closing both hazards is easier to keep right than two, and the alias is not the invocation the tool's own documentation uses. Naming the package is also the rule `audit/SKILL.md` already states for a tool whose bin name differs from its package name.

### 3. Each record keeps its own consequence clause

The four records share the parenthetical and differ in what a zero-module cruise looks like for that check - zero violations, no cycles, an empty graph, a hub count of nothing. Only the parenthetical and the new placeholder clause change; each trailing clause stays as written, because it is the sentence that makes the failure legible for that check.

## Verified tool facts

Rows for the three runners' package options are already verified in `2026-08-10-typescript-test-security-lens-design.md` under `## Verified tool facts`, and are referenced rather than restated. Two facts are new here.

| Fact | Source |
|---|---|
| npm carries a package named `depcruise`, sole version `1.0.0`, published 2025-07-23 by `debugducky` (Aikido Security), which is neither of `dependency-cruiser`'s maintainers (`sverweij`, `foureightone`). It describes itself as "Placeholder to prevent dependency confusion", declares `bin: {"depcruise": "cli.js"}`, and that file's whole body is one `console.log` of a misconfiguration notice with no non-zero exit. So a runner fetching it succeeds, runs it, and gets a zero exit with nothing on stdout that a check can read - not the clean failure a missing tool gives | npm registry metadata and the published tarball, read without executing it |
| `dependency-cruiser`, latest `18.2.0`, declares six bins, among them `depcruise` (the name its documentation uses) and a `dependency-cruiser` alias equal to its package name | npm registry metadata for `dependency-cruiser` |

`madge` was checked against the same hazard and is clear: its bin name equals its package name, and the `madge` package at `8.0.0` is the real tool. It stays as written.

## Out of scope

**Yarn 1 has no `dlx`.** Yarn classic's documented command list carries 43 commands and `dlx` is not among them; `dlx` is a Yarn 2+ command. `audit/SKILL.md`'s runner table says "`yarn dlx <tool>` for yarn" without qualification, so a Yarn 1 partition has no one-shot runner and the table does not say so. That is one defect in one shared sentence rather than four in the records, the records here match family precedent by naming `yarn dlx`, and #29 already requires a pnpm or yarn target, which is where it surfaces empirically. Left for a follow-up issue against `audit/SKILL.md`.

**The taxonomy that misroutes a foreign-registry package** is #28. This change is consistent with it either way: `dependency-cruiser` is a package in the partition's own registry, which is the kind the taxonomy already handles.

## Acceptance

- The four records each give three concrete pinned forms, every one naming `typescript` alongside `dependency-cruiser`.
- `grep -rn "dlx" .agents/skills/` shows no remaining "equivalent" gesture.
- No frontmatter changes, so the matrix edge set is untouched and the traceability gate is unaffected.

## Files

- `.agents/skills/arch-audit/checks/layering.md`
- `.agents/skills/arch-audit/checks/cycles.md`
- `.agents/skills/arch-audit/checks/coupling.md`
- `.agents/skills/arch-audit/checks/over-decomposition.md`
