# Tooling that needs a materialized dependency tree ([#19](https://github.com/mesagroup/ai-agent-development-handbook/issues/19))

**Status:** draft 2026-08-06. Unblocks [#5](https://github.com/mesagroup/ai-agent-development-handbook/issues/5), which cannot add a TypeScript tooling entry to `test/coverage-reach` without the policy this spec settles.

## Problem

[#17](https://github.com/mesagroup/ai-agent-development-handbook/pull/17) replaced a hardcoded `uv run --with <tool>` with the one-shot runner of the partition's own package manager, and `audit/SKILL.md` now classifies a `tooling:` name by **kind**: a registry package a runner can fetch, a subcommand of the target's own package manager, or a standalone binary in no registry. That axis answers *how do I obtain this tool*.

It does not answer the question the fixture runs kept failing on: *what must be present in the target before the tool can produce an answer*. Two cases were observed. On the single-package target, `npx vitest run` fails because the project's `vitest.config.ts` imports from `vitest/config`, which resolves out of a `node_modules` that a read-only clone does not have; a one-shot runner can fetch `vitest` and cannot satisfy the config's own imports. On the polyglot monorepo, `pip-audit` and `pip-licenses` need materialized packages, and the fixture recorded those checks `no-evidence` rather than guessing.

The two axes are orthogonal, and the family has vocabulary for only one of them:

| Tool | Fetchable by a one-shot runner | Answers from a read-only clone |
|---|---|---|
| `knip` | yes, a registry package | no, it wants `typescript` and `@types/node` installed |
| `osv-scanner` | no, a standalone binary | yes, it reads the lockfile directly |

So a run can hold a tool it cannot use, and can use a tool it cannot hold. With no way to say which, an agent discovers the difference by failing, and the failure lands in the report as `no-evidence` for a check that was never going to run - indistinguishable from a check whose tooling merely happened to be absent.

`no-evidence` is the honest status and the reports do say so, which is the `audit-core` status rule working as designed. But a foreign-repository audit returning `no-evidence` for coverage, licences and vulnerabilities has told the reader very little, and the reason it cannot do better is a rule this family chose: [#8](https://github.com/mesagroup/ai-agent-development-handbook/issues/8) made writing to the target a stated violation, and installing dependencies writes to the target.

## Decisions

### 1. A tool's requirement is a tier, ordered, with the common case unnamed

Three tiers. The default carries no name because most tools are in it and an unmarked record should mean the ordinary thing.

| Tier | The tool needs | Illustrative members |
|---|---|---|
| *(default, unnamed)* | Only what a read-only clone contains: source, manifests, lockfiles | `ruff`, `semgrep`, `osv-scanner`, `gitleaks`, `depcheck`, `@cyclonedx/cdxgen` |
| `resolved-tree` | The dependency graph materialized, so package metadata can be read | `pip-licenses`, `pnpm licenses list`, `knip` |
| `target-execution` | The tree, and running the target's own code | `pytest-cov`, `coverage.py`, `mutmut`, `diff-cover` |

`target-execution` implies `resolved-tree`: a tool that runs the target's test command needs the tree that command imports from.

The membership above is illustrative. Every one of the tool names the records currently carry is classified against that tool's own documentation during implementation, not against whether an invocation happened to succeed, for the reason the repository already records about `cyclonedx-npm`: a name that resolves and runs is not thereby the tool you meant. Three records already carry verified prose on this point and their classifications are read from it rather than re-derived - `deps/licenses` on every licence tool needing materialized metadata, `deps/hygiene` on `depcheck` answering from source where `knip` does not, and `deps/vulnerabilities` on which scanners read a lockfile directly.

The tier is a property of the tool, so it belongs with the tool, in the record that names it. It is not a property of the check: `deps/hygiene` offers `depcheck` and `knip` for the same question and they sit in different tiers, which is what rules out recording this once per check.

### 2. Never install into the target, and `git worktree add` is not an exception

The no-writes invariant is unchanged and stays unconditional, still checked with `git status --porcelain` at `target_root` rather than promised.

One addition, stated explicitly because it is the first thing an agent reaches for when told to get a second copy of a repository cheaply: **`git worktree add` is barred.** It writes `.git/worktrees/`, so it is a write to the target's git administrative state. The invariant already names the git history alongside the working tree; this makes the consequence impossible to miss, since the command creates no visible working-tree delta and would therefore pass the `git status --porcelain` comparison that is supposed to catch exactly this.

### 3. Two grants, default off, resolved at scope time, carried in the dispatch

`resolved-tree` and `target-execution` are separate grants. Holding the first does not confer the second.

They are resolved once in step 0, alongside the opt-in list and for the same reason: a dispatched agent has nobody to confirm with, so a permission it has to ask for is a permission it cannot obtain. The resolved grants travel in the fan-out payload. A non-interactive run holds neither, which follows the existing default rather than inventing one.

The split is what keeps the grants meaningful. Materializing a tree with scripts disabled reads package metadata and no first-party code. Running the target's test suite executes arbitrary code from a repository we were invited to read. A single permission covering both would mean that granting a licence scan also granted running a stranger's test suite in our environment, and nobody asked that question would understand they were answering it.

### 4. Reconstruct outside the target, and say so in the report

Under a grant, the tree is materialized in a scratch directory that must not resolve under `target_root` - the same refusal `out_path` already gets, for the same reason. The target's working tree is copied there and the install runs against the copy.

The report states that the graph was **reconstructed** rather than read, with the resolver command and whether the lockfile was frozen. A reconstructed graph is evidence, and it is weaker evidence than a lockfile read in place: it can differ from what the audited team actually has installed, and a reader who is not told cannot discount it.

### 5. Install scripts belong to the execution grant

The resolve step runs with `--ignore-scripts`, or that package manager's equivalent.

A `postinstall` hook is third-party code from the target's dependency graph executing in the audit environment. That is the `target-execution` tier by definition, and the fact that it arrives during an install rather than during a test run does not change what it is.

The consequence is deliberate and it is the least comfortable part of this design: where `--ignore-scripts` yields an unusable tree, which is the normal outcome for a graph with native builds, that is not a reason to drop the flag under a `resolved-tree` grant. The run either holds `target-execution` as well, or reports `no-evidence`. A licence audit can therefore stall on a grant whose name sounds like it is about tests. The alternative is worse: a `resolved-tree` grant that silently executes whatever a dependency's install hook contains is not the permission the user was asked for.

### 6. `no-evidence` carries a reason; the status scale does not grow

`audit-core` is emphatic that the domain's clean value, `no-evidence` and `not-applicable` must never collapse into one another. A fourth status would be that same collapse running backwards, so the scale stays as it is and `no-evidence` takes a required reason from a closed set of three:

| Reason | Means | Fixable by |
|---|---|---|
| `not-permitted` | The check needed a grant this run does not hold | Re-running with the grant |
| `tool-unavailable` | No candidate tool could be obtained: unfetchable, not installed, or no network | The audit environment |
| `tool-failed` | A tool ran and errored, or returned nothing parseable | Neither; it needs investigation |

This generalises a distinction one record already draws in prose. `deps/vulnerabilities` says of a retired registry endpoint and a missing scanner that they "are both `no-evidence`, but only the second is fixable by the audit environment", and then has to tell the reader to note which case applied, because the matrix has nowhere to put it. Now it has somewhere.

The status cell renders the reason with the status, as `no-evidence (not-permitted)`. The tool log names the specific grant that was missing, since the matrix cell has room for the class and not for which of the two grants it was.

### 7. The tier is recorded in frontmatter and validated against `tooling:`

One optional key, mapping a tier to tool names, flat across languages:

```yaml
tooling:
  python: [pip-licenses]
  typescript: ["pnpm licenses list", "@cyclonedx/cdxgen"]
needs:
  resolved-tree: [pip-licenses, "pnpm licenses list"]
```

An omitted tier is a positive claim that no tool of this record needs it. That is what makes a partial sweep unacceptable: a record left unclassified does not read as unclassified, it reads as clean. Every record carrying `tooling:` is classified in this change, which is what keeps the claim true from the moment the key exists.

The names are duplicated between the two keys on purpose, and the duplication is the point: `scripts/audit_checks.py` asserts that every name under `needs:` appears somewhere in `tooling:`, so a rename or a typo fails the gate instead of quietly describing a tool the record does not offer. The rules the loader enforces are that `needs:` is a mapping, that each key is a known tier, that each value is a list of strings, that every name occurs in `tooling:`, that no name occurs under two tiers, and that `needs:` without `tooling:` is an error.

`tooling:` itself is untouched. Folding the tier into each entry by turning the bare strings into objects would put both facts in one place with no duplication, and it would touch every record in the family, both scripts, the test fixtures and the integrity gate to express something a four-line validation already catches.

## Scope

| File or group | Change |
|---|---|
| `audit-core/SKILL.md` | Step 0: the two grants and the scratch-directory refusal. Step 1: the tier axis as orthogonal to the kind axis, reconstruct-outside, `--ignore-scripts`, and scripts belonging to the execution grant. Step 2: the `no-evidence` reason vocabulary. The authoring section: `needs:` in the frontmatter list. The cross-cutting no-writes rule: `git worktree add` barred. |
| `audit/SKILL.md` | Grants resolved once at step 0 beside the opt-in list, carried in the fan-out payload; the report template gains a grants line and renders the reason on `no-evidence`. |
| `docs/audit/sweep-obligations.md` | A row per obligation this change adds to `audit-core`, with its disposition. |
| The records carrying `tooling:` | Classify every tool name, add `needs:` where a tier applies, and revise `## Tooling fallback` where the tier changes what to run or in what order. |
| `scripts/audit_checks.py` | The field, the validation rules above, the `Check` dataclass, and the frontmatter table in the module docstring. |
| `tests/scripts/` | A case per validation rule. |
| `CLAUDE.md` | The check-records paragraph gains `needs:`. |

No traceability matrix rows change. This is skill mechanics rather than a handbook clause, so no check gains or loses a `handbook:` citation and the edge set is untouched.

## Verification

The mechanical half is covered by the existing gates: the new loader rules have unit tests, the integrity gate runs `--check`, and `tests/test_sweep_obligations.py` holds the new ledger rows to the same anchor-and-quotation standard as the rest.

The policy half is prose an agent reads, and this repository has no foreign target to run it against, so **there is no end-to-end verification that a reconstructed-tree audit behaves as specified.** What can be verified is that the obligations are stated, that the ledger accounts for each of them, and that no record makes a tier claim contradicted by its own `tooling:`. The PR says this rather than implying a fixture run happened.

The sweep-obligations ledger earns its keep here for the first time. #19 is the first change since it was written that adds obligations to `audit-core`, and the ledger's premise is that an obligation the sweep silently fails to restate leaves no trace in the file that dropped it. Skipping the rows would make the ledger stale in exactly the way it exists to prevent.

## Acceptance criteria, mapped

| Criterion | Where it is met |
|---|---|
| `audit-core` distinguishes manifest-and-lockfile tools from tools needing a materialized tree | Decision 1, stated in step 1 as an axis orthogonal to the existing kind classification |
| A stated, logged policy for the second class that does not silently write into the target | Decisions 2, 3, 4 and 5: the invariant holds, the grants are explicit and default off, the tree is reconstructed outside `target_root`, and the report records that it was |
| Check records note which of their tools need a resolved tree | Decision 7, across every record carrying `tooling:`, enforced by the loader |
| The coverage column or the tool log distinguishes "not permitted" from "would not install" | Decision 6: `not-permitted` against `tool-unavailable`, in the status cell, with the specific grant in the tool log |

## Related

- [#17](https://github.com/mesagroup/ai-agent-development-handbook/pull/17) introduced the per-package-manager runner and surfaced this during fixture verification.
- [#8](https://github.com/mesagroup/ai-agent-development-handbook/issues/8) established the no-writes-to-the-target invariant this has to respect.
- [#5](https://github.com/mesagroup/ai-agent-development-handbook/issues/5) is blocked on decision 1: `test/coverage-reach` prescribes running the project's own test command with coverage, which is `target-execution`, and it cannot gain a TypeScript entry until there is a way to say so.
