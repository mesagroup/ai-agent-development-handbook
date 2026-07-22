# Part 8 — Security, Dependencies & Supply Chain

The parts so far make the system correct and measurable. This one keeps it safe to ship and safe to run. A system can be well-tested, well-evaluated, and still leak a credential, ship a dependency it has no legal right to distribute, or hand a malicious pull request the keys to its own pipeline — and none of those failures show up in a unit test or an eval. They need their own lens. There are three surfaces (your own code, what you depend on, and the pipeline that builds you) and one principle that ties them together: **find where untrusted input meets a dangerous operation, know what you depend on, and make the pipeline that builds you trustworthy.**

## First-party code: a finding is a path from source to sink

The unit of a real security finding is a **path from an untrusted source to a dangerous sink** — not a scary-looking function in isolation. Name both or it isn't a finding: a `subprocess` call on a hardcoded constant is not command injection; a real dataflow a scanner missed is the finding that matters. Verify both directions against the actual code.

- **Sources** (where untrusted data enters): HTTP handlers, CLI arguments, file and object-store reads, message queues, environment, and — the one specific to agents — **model and tool outputs.** Treat what an LLM or a tool returns as untrusted input, not as trusted data; it can carry injected instructions or hostile content.
- **Sinks** (dangerous operations): shell/subprocess, `eval`/`exec`, deserialization (`pickle`, unsafe `yaml.load`), SQL, filesystem paths, outbound requests (SSRF), template rendering.
- **Neutralize at the sink** (parameterized queries, an argument-list subprocess with no shell, safe deserialization, hardened XML) and **validate/canonicalize at the boundary** (allowlists, path-containment checks against traversal and zip-slip, URL-host allowlisting against SSRF).

## Secrets: never committed, and rotate — don't just delete

No credential belongs in source, defaults, tests, fixtures, or notebooks. A secret *read from* the environment is fine; a secret *literal* is not. And the rule that is easy to get wrong: a committed secret is **live until rotated.** Deleting the line leaves it in git history, where it is still exploitable — rotate the credential at its provider first, then remove it, then purge history if it was ever pushed. This is the one finding that is never merely "suppressed."

## Depend only on what you can account for

Know your third-party surface **transitively**, because most vulnerabilities and most copyleft licenses arrive through a dependency's dependency, not your own `pyproject`. Four things are worth auditing:

- **Licenses** — each dependency's license against your project's own license and distribution model. Copyleft pulled into a permissive, distributed artifact is a legal problem, not a style one; missing/unknown license metadata is its own risk.
- **Known vulnerabilities** — advisories affecting the *resolved* versions, with the fixed version if one exists.
- **Freshness** — outdated, yanked, or end-of-life versions.
- **Hygiene** — declared-but-unused, used-but-undeclared (silently relying on a transitive), and conflicting pins.

**Pin for reproducibility.** A floating direct dependency means a build that resolved clean yesterday can pull a vulnerable or newly-copyleft version today; the lockfile is the record of what actually ran. And the AI-specific extension: **the model and the provider are dependencies too.** Pin model versions where the provider allows it, record which model produced a given result, and know your providers' data-retention terms — a silent model upgrade is an unpinned dependency that can move your eval numbers out from under you.

## The pipeline is a privileged environment

CI is both the merge gate and a privileged runtime holding your secrets, which makes it an attack surface in its own right. The question to keep asking is: *what could a malicious pull request, or a compromised third-party action, do with this pipeline's permissions?*

- **Least privilege** — the pipeline token defaults to read-only; widen to write only the single job that genuinely needs it.
- **Pin third-party actions to an immutable commit, not a mutable tag.** A `@v4` or `@main` reference can change under you; a full commit SHA cannot.
- **Trigger safety** — never run untrusted PR code with secrets in scope. Keep the privileged, secret-bearing steps off any path an outside contributor can influence.
- Prefer short-lived, federated credentials (OIDC and the like) over long-lived stored secrets where the platform supports it.

## Turn every fix into a gate

Every fix on this page is one-time; the *class* of problem is forever. A credential scrubbed today is re-committed next month; a dependency bumped today drifts again; a locked-down workflow is loosened by the next author who needs a quick win. So the highest-leverage move on all three surfaces is the same one the rest of the handbook keeps returning to: **encode the standard as an executable check and wire it into CI and pre-commit** — a SAST plus secret scan for first-party code, a CVE-plus-license gate for dependencies, a workflow linter and an action-pin checker for the pipeline. A cleanup you did not turn into a gate is a cleanup you will do again. This is the [make-the-standard-executable](lifecycle.md) discipline applied to the safety surfaces.

## The verification side

Each surface here has a counterpart that *verifies* it against the real artifacts — the first-party code, the resolved dependency graph, the workflow files and their branch-protection reality. Treat this page as the practice and that verification as the standing check: run it periodically, report-only first to see where the repo hurts, then fix one surface at a time in its own reviewed change (see [Part 1](lifecycle.md) on auditing as a periodic health check). Severity is context: the same injection pattern is Critical on an internet-facing surface and a code-smell in a local dev script, so judge each finding by whether its path is actually reachable and what it reaches.

## See also

- [Part 1 — Lifecycle](lifecycle.md) — CI gates, the "make the standard executable" principle, and periodic audits.
- [Part 4 — Observability](observability.md) — errors that don't leak secrets/PII, and no swallowed exceptions hiding a security failure.
- [Part 5 — Evaluation](evaluation.md) — behavioral injection-resistance as an eval dimension.
- [Handbook index](README.md).
