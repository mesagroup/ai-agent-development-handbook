---
name: deps-audit
description: "Audit a Python project's third-party dependency surface: license compatibility (copyleft, unknown/missing licenses), known vulnerabilities (CVEs), version freshness (outdated / yanked / unpinned), and hygiene (unused / undeclared / conflicting deps). Use when checking whether the dependency tree is legally and securely shippable, before a release, or when the user asks to audit licenses or dependencies. Produces a findings matrix and drives remediation. Runs on the audit-core engine."
---

# Dependency Audit (licenses + supply chain)

A domain specialization of **[audit-core](../audit-core/SKILL.md)** — read that first; it owns the loop (scope → parallel evidence → findings matrix → plan → subagent-driven fixes → review → PR). This skill supplies the dependency lens. It owns the whole *third-party* surface; first-party code security belongs to `security-audit`, which cross-links the CVE overlap here.

**Announce:** "I'm using the deps-audit skill (on the audit-core engine) to audit the dependency surface."

**Bash rule:** never pass a line starting with `#` to the Bash tool (you or any subagent).

## 1. Subject & scope

The project's declared and resolved dependency graph, and the licenses/vulnerabilities/freshness/usage of every node in it. Establish two things first, because they change the verdicts:

- **The project's own license** (`pyproject.toml` `[project] license` / classifiers, or `LICENSE`). Copyleft-compatibility is judged relative to it.
- **Distribution model** — is this a library published to an index (copyleft in a dependency is then high-stakes) or an internal/app deployment (copyleft is usually lower-stakes, but still policy-dependent)? Ask if unclear.

Slice the parallel evidence pass by dependency group (main / dev / optional-extras) or by dimension.

## 2. Dimensions (findings-matrix columns)

- **License compatibility** — each dependency's license vs the project's license/policy: copyleft (GPL/AGPL/LGPL) pulled into a permissive project, "unknown"/missing license metadata, non-OSI or source-available licenses, license *changes* across a version bump.
- **Known vulnerabilities** — CVEs / advisories affecting the *pinned/resolved* versions, with the fixed version if one exists.
- **Freshness** — outdated (a newer release exists), yanked, or EOL versions; unpinned/floating direct dependencies (reproducibility + drift risk).
- **Hygiene** — declared-but-unused dependencies, used-but-undeclared (relying on a transitive), duplicate/conflicting pins, dev deps leaking into runtime.
- **Inventory** (optional) — SBOM completeness.

## 3. Evidence sources & tooling

**Detect** the project's package manager (`uv` / `pip` / `poetry` — check for `uv.lock`, `poetry.lock`, `requirements*.txt`) and use its resolved graph as ground truth (transitive deps matter — most CVEs and copyleft licenses arrive transitively).

Run in the parallel evidence pass (prefer a tool the project already has; fall back otherwise). Instruct subagents: never pass `#`-comment lines to Bash.
- **Licenses:** `pip-licenses` (with `--format` for SPDX-ish output), or read each installed dist's `*.dist-info/METADATA` (`License` + `Classifier: License ::`). Map to SPDX ids; flag `UNKNOWN`.
- **Vulnerabilities:** `pip-audit` (PyPA, reads the environment or a requirements/lock file) or `safety`. Capture advisory id, affected range, and fixed version.
- **Freshness:** `uv pip list --outdated` / `pip list --outdated`; check the lockfile for floating direct pins; check PyPI for yanked releases.
- **Hygiene:** `deptry` (unused / missing / transitive / misplaced) or an import-vs-declared cross-check.
- **SBOM (opt-in):** `cyclonedx-py` or the tool's native SBOM export.

Read `pyproject.toml` (`[project]` deps, `optional-dependencies`, dependency groups) and the lockfile. Record exact resolved versions as the evidence pointer for every row.

## 4. Status scale + severity rubric

Status per row: **ok / warn / violation** (for licenses: allowed / review-needed / disallowed).

- **Critical** — a disallowed/incompatible license in a dependency that is actually shipped/distributed; a High/Critical CVE with a fix available; a dependency with no resolvable license in a published library.
- **Important** — a Medium CVE; copyleft in a distributed artifact pending legal review; an unpinned *direct* runtime dependency; a yanked resolved version; a used-but-undeclared dependency.
- **Minor** — outdated-but-safe versions; a dev-only CVE not shipped to users; unused declared deps; missing SBOM.

Suppressions (a known-accepted CVE, an approved license exception) must be explicit and recorded with a reason — never silently dropped.

## 5. Fix patterns (and CI implications)

Most fixes here **touch `pyproject.toml` / the lockfile / CI config**, so they are **not** docs-only: the domain gate is "the lockfile still resolves **and** the test suite passes." Route them through the normal install + lint/typecheck/test CI.
- Bump/pin to a fixed version; regenerate the lock (`uv lock` / equivalent) and re-run tests.
- Replace or remove a disallowed-license or unused dependency; update imports; re-test.
- Add a **license allowlist/policy** and/or a CI gate (`pip-audit`, `pip-licenses` check) so the finding can't silently recur — this is the highest-leverage fix.
- Docs-only outputs: a `NOTICE`/`THIRD-PARTY-LICENSES` file, a generated SBOM, or the audit report itself.

## 6. Review dimensions (Phase-5 specialized reviewers)

- **License-compatibility correctness** — is each verdict right for the project's own license and distribution model? (copyleft nuance, LGPL dynamic-linking, dual licenses)
- **CVE accuracy** — correct advisory id, affected range, and fixed version; no stale or false-positive advisories.
- **Graph correctness** — direct vs transitive attribution is right; a transitive-only finding isn't pinned as if it were direct.
- **No regression** — the lockfile still resolves and tests pass after bumps/removals.

## 7. Opt-in sub-audits

- **SBOM generation** (CycloneDX) as a deliverable — enable via argument or ask the user.
- **Transitive-license deep dive** (full graph, not just direct) — default on for published libraries, ask otherwise.
