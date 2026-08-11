---
name: deps-audit
description: "Audit a project's third-party dependency surface: license compatibility (copyleft, unknown/missing licenses), known vulnerabilities (CVEs), version freshness (outdated / yanked / unpinned), and hygiene (unused / undeclared / conflicting deps). Use when checking whether the dependency tree is legally and securely shippable, before a release, or when the user asks to audit licenses or dependencies. Produces a findings matrix and drives remediation. Runs on the audit-core engine."
---

# Dependency Audit (licenses + supply chain)

A domain specialization of **[audit-core](../audit-core/SKILL.md)** - read that first; it owns the loop (scope → parallel evidence → findings matrix → plan → subagent-driven fixes → review → PR) and the cross-cutting rules. The checks are records in [`checks/`](checks/) beside this file; load the ones your slice needs, not the directory. This skill supplies the dependency lens. It owns the whole *third-party* surface; first-party code security belongs to `security-audit`, which cross-links the CVE overlap here.

**Core principle:** the license verdict here is relative, not absolute - whether a copyleft dependency is a problem at all is judged against *this* project's own license and distribution model, not a universal rule. Most of the risk arrives transitively: a CVE or a copyleft license several levels down in the resolved graph binds the project exactly as much as one in a direct dependency, so the resolved graph, not the declared one, is ground truth.

**Announce:** "I'm using the deps-audit skill (on the audit-core engine) to audit the dependency surface."

**Not for:** first-party application-code security (use `security-audit`) or the pipeline's own supply chain (use `ci-audit`).

**Subject:** the project's declared and resolved dependency graph, and the licenses/vulnerabilities/freshness/usage of every node in it. Establish two things first, because they change the verdicts:

- **The project's own license** (the partition's manifest - e.g. `pyproject.toml` `[project] license` / classifiers for a Python partition, `package.json`'s `license` field for a JavaScript one - or a top-level `LICENSE`). Copyleft-compatibility is judged relative to it.
- **Distribution model** - is this a library published to an index (copyleft in a dependency is then high-stakes) or an internal/app deployment (copyleft is usually lower-stakes, but still policy-dependent)? Ask if unclear.

**Detect** the package manager and lockfile from the project inventory, which already records both per partition, and use its resolved graph as ground truth (transitive deps matter - most CVEs and copyleft licenses arrive transitively). A partition may declare dependencies in an ecosystem the rest of the repository does not use, and each declaration site is its own graph: a repository with a JavaScript lockfile and two Python requirements files has three, and auditing only the first reports the other two as clean. A manifest commonly separates dependency classes - production, optional or extras, and dev or peer groups - and each is a candidate for the resolved graph; scope out dev-only dependencies only if the distribution model justifies it, since a dev-dependency-only CVE or license issue is a routine finding otherwise missed.

Every `deps` check is **global**, which means whole-subject rather than single-graph: the subject is every resolved graph the target declares, taken together, so one agent walks all of the declaration sites and no check is sliced per partition. Global is not a licence to audit one graph and call the subject covered. **A workspace is the case where a single command quietly breaks that rule**, because the package manager's own subcommands disagree with each other about it: on one pnpm workspace `pnpm audit` and `pnpm licenses list` covered all 9 manifests by default while `pnpm outdated` covered only the root's 10 declared dependencies out of 254, reporting nothing to say the rest were never read. Check each command against the manifest count you established here, and reach for its recursive form (`-r`, `--workspaces`, the manager's equivalent) rather than assuming the default matches the subject.

Status per row: **ok / warn / violation** (for licenses: allowed / review-needed / disallowed). Suppressions (a known-accepted CVE, an approved license exception) must be explicit and recorded with a reason - never silently dropped.

Most fixes here **touch the manifest / the lockfile / CI config**, so they are **not** docs-only: the domain gate is "the lockfile still resolves **and** the test suite passes." Take the actual install and test commands from the inventory's package manager and test runner rather than assuming one ecosystem's. Add a **license allowlist/policy** and/or a CI gate (a vulnerability/license scanner matched to the partition's ecosystem, e.g. `pip-audit` / `pip-licenses` for Python) so the finding can't silently recur - this is the highest-leverage fix. Docs-only outputs: a `NOTICE`/`THIRD-PARTY-LICENSES` file, a generated SBOM, or the audit report itself.

**Opt-in deliverable:** SBOM generation (CycloneDX) as a deliverable - enable via argument or ask the user. The opt-in *checks* - SBOM completeness and the transitive-license deep dive - are `deps/inventory` and `deps/transitive-licenses`, loaded like any other.
