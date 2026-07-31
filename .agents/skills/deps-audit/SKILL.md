---
name: deps-audit
description: "Audit a Python project's third-party dependency surface: license compatibility (copyleft, unknown/missing licenses), known vulnerabilities (CVEs), version freshness (outdated / yanked / unpinned), and hygiene (unused / undeclared / conflicting deps). Use when checking whether the dependency tree is legally and securely shippable, before a release, or when the user asks to audit licenses or dependencies. Produces a findings matrix and drives remediation. Runs on the audit-core engine."
---

# Dependency Audit (licenses + supply chain)

A domain specialization of **[audit-core](../audit-core/SKILL.md)** - read that first; it owns the loop and the cross-cutting rules. The checks are records in [`checks/`](checks/) beside this file; load the ones your slice needs, not the directory. This skill supplies the dependency lens. It owns the whole *third-party* surface; first-party code security belongs to `security-audit`, which cross-links the CVE overlap here.

**Announce:** "I'm using the deps-audit skill (on the audit-core engine) to audit the dependency surface."

**Subject:** the project's declared and resolved dependency graph, and the licenses/vulnerabilities/freshness/usage of every node in it. Establish two things first, because they change the verdicts:

- **The project's own license** (`pyproject.toml` `[project] license` / classifiers, or `LICENSE`). Copyleft-compatibility is judged relative to it.
- **Distribution model** - is this a library published to an index (copyleft in a dependency is then high-stakes) or an internal/app deployment (copyleft is usually lower-stakes, but still policy-dependent)? Ask if unclear.

**Detect** the project's package manager (`uv` / `pip` / `poetry` - check for `uv.lock`, `poetry.lock`, `requirements*.txt`) and use its resolved graph as ground truth (transitive deps matter - most CVEs and copyleft licenses arrive transitively). Read `pyproject.toml` (`[project]` deps, `optional-dependencies`, dependency groups) and the lockfile.

Every `deps` check is **global**: the subject is one resolved dependency set, not a partitioned tree, so there is no per-partition slice to fan out to.

**Status per row:** ok / warn / violation (for licenses: allowed / review-needed / disallowed). Suppressions (a known-accepted CVE, an approved license exception) must be explicit and recorded with a reason - never silently dropped.

Most fixes here **touch `pyproject.toml` / the lockfile / CI config**, so they are **not** docs-only: the domain gate is "the lockfile still resolves **and** the test suite passes." Route them through the normal install + lint/typecheck/test CI. Add a **license allowlist/policy** and/or a CI gate (`pip-audit`, `pip-licenses` check) so the finding can't silently recur - this is the highest-leverage fix. Docs-only outputs: a `NOTICE`/`THIRD-PARTY-LICENSES` file, a generated SBOM, or the audit report itself.

**Opt-in deliverable:** SBOM generation (CycloneDX) as a deliverable - enable via argument or ask the user. The opt-in *checks* - SBOM completeness and the transitive-license deep dive - are `deps/inventory` and `deps/transitive-licenses`, loaded like any other.
