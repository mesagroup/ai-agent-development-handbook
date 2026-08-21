---
id: deps/vulnerabilities
domain: deps
locality: global
evidence: >-
  Capture advisory id, affected range, and fixed version. Where no route
  answers, note which case produced that status: a retired endpoint and a
  missing scanner are both `no-evidence`, but only the second is fixable by
  the audit environment.
handbook:
  - security-supply-chain/depend-only-on-what-you-can-account-for-a
routes:
  - lang: python
    kind: command
    tool: pip-audit
    argv_by_partition:
      pip: [pip-audit, "-r", requirements.txt, "--no-deps", "--disable-pip"]
      pylock: [pip-audit, "--locked", "."]
    note: >-
      Which `pip-audit` mode applies is decided by what the partition
      actually locks with, and picking the wrong one audits nothing at exit 0.
      `pip-audit --locked .` reads a PEP 751 lock file (`pylock.*.toml`) and
      the project's `pyproject.toml`, and nothing else: it does not read
      `uv.lock`, `poetry.lock`, `Pipfile.lock` or a requirements file, so a
      target locked with uv or poetry alone is not served by `--locked` and is
      the ordinary case rather than the exotic one.
      `pip-audit -r <requirements> --no-deps --disable-pip` avoids
      provisioning the throwaway virtualenv the un-narrowed form needs:
      `--no-deps` requires every requirement to be pinned to an exact
      version, and `--disable-pip` requires either a hashed requirements file
      or `--no-deps` already given, so the two are meant to be used together.
      Its soundness depends on what the requirements file itself contains,
      not on the flags: pointed at a file a lockfile export produced with
      full resolution - `uv export --frozen` writes the whole resolved set,
      directs and transitives together - it audits everything the lock pins;
      pointed at a requirements file that declares only direct pins, it
      audits only those, and a transitive-only advisory is invisible rather
      than reported as a gap. Name which shape the file has before
      prescribing `--no-deps`; prescribing it without that turns a complete
      answer into a silently partial one. The partitions named nowhere above
      are the ones with neither input - a uv, poetry or pipenv lock and no
      exported requirements - where `pip-audit` has nothing it can read on a
      read-only clone, and the check is `no-evidence` unless another tool
      answers it. Run `pip-audit` with no arguments and it audits whatever
      environment it was launched from, which on a foreign target is the
      audit environment rather than the subject - not evidence about the
      target at all, so don't. The python lens smoke run reports `no-evidence`
      for this check on the pip and uv partitions, and the reason is a host
      fault rather than anything about this command: `ensurepip` aborts with
      `SIGABRT` whenever `pip-audit -r` has to provision its own virtualenv,
      with and without `--no-deps`. Provisioning is the step this pair removes,
      so the pair itself is unexercised there rather than tested and found
      wanting - which is why the observation belongs beside the command it is
      about rather than beside the un-narrowed form below.
  - lang: python
    kind: command
    tool: pip-audit
    argv: [pip-audit, "-r", "<requirements>"]
    disposition: superseded
    note: >-
      Where the partition has a requirements file,
      `pip-audit -r <requirements>` parses it and provisions its own
      throwaway virtualenv to resolve it, so it needs network rather than the
      target's tree. Superseded by the narrowed form above rather than
      offered beside it, which is why the placeholder is safe here and the
      command that runs names the file.
  - lang: python
    kind: procedure
    tool: safety
    needs: resolved-tree
    note: >-
      The alternative to `pip-audit`, named without a command line, so there
      is no argv to declare and a `kind: command` route would have to invent
      one. Its tier is `resolved-tree` because the completeness it claims is
      only ever claimed about a scan of an installed environment: its own CI
      guidance installs the dependencies before scanning, precisely so the
      scan reaches the transitive packages that arrive during installation,
      so pointed at a lone `requirements.txt` it under-reports silently
      instead of failing. It also requires authentication and is unusable in
      an unauthenticated audit whatever else is true, which is a separate
      reason from its tier.
  - lang: typescript
    kind: command
    tool: npm audit
    argv: [npm, audit]
    note: >-
      Prefer the audit subcommand of the package manager the inventory
      records for the partition, which is already installed and already reads
      the lockfile that is present, but **read its version first**: npm
      retired the legacy audit endpoints (`/-/npm/v1/security/audits` and
      `/-/npm/v1/security/audits/quick`) on 2026-07-15 after brownouts from
      April, so a client still calling them returns 410 rather than a result.
      `npm audit` is unaffected, npm having moved its own client to
      `/-/npm/v1/security/advisories/bulk` first. Each of these subcommands
      belongs to its own package manager rather than being a publishable
      package, so a one-shot runner cannot fetch any of them, and
      `npm audit` is not a stand-in for the others even where the `npm`
      binary happens to be installed: it resolves from `package-lock.json`,
      which a pnpm or yarn partition does not have.
  - lang: typescript
    kind: command
    tool: pnpm audit
    argv: [pnpm, audit]
    note: >-
      `pnpm audit` was expected to work only from **pnpm 11**, which rewired
      to the endpoint `npm audit` moved to, and to fail on pnpm 10 or
      earlier. **Run it and read the output rather than gating on the
      version**: on 2026-08-11 a pnpm **9.15.9** partition returned 106
      advisories - 3 critical, 47 high, 59 moderate, 9 low - straight from
      `pnpm-lock.yaml` with no `node_modules`, so the version rule would have
      written off a check that answers in full. Treat a retired-endpoint
      failure as something to observe, not to predict: where it does fail,
      that is `no-evidence (tool-unavailable)` and never a finding about the
      target.
  - lang: typescript
    kind: command
    tool: yarn npm audit
    argv: [yarn, npm, audit]
    note: >-
      Yarn Berry's maintained path, and the same preference the `npm audit`
      route above carries: the partition's own package manager, reading the
      lockfile that is already there.
  - lang: typescript
    kind: command
    tool: yarn audit
    argv: [yarn, audit]
    disposition: forbidden
    note: >-
      Yarn Classic's `yarn audit` calls a retired endpoint and Yarn 1 is
      unmaintained, so it will not be fixed - do not prefer it, and do not
      read its failure as a finding about the target.
  - lang: typescript
    kind: procedure
    tool: osv-scanner
    note: >-
      For a Yarn Classic partition, or any partition whose own audit
      subcommand does fail, `osv-scanner` is the option that works: it reads
      `bun.lock`, `package-lock.json`, `pnpm-lock.yaml` and `yarn.lock`
      directly, so it needs nothing installed in the target and does not
      depend on a registry audit endpoint at all, which is why this route
      carries no tier. It is distributed as a standalone binary rather than a
      registry package, so a one-shot runner cannot supply it - an audit
      environment expected to cover those partitions needs it installed in
      advance. Where it is absent, the check is `no-evidence`, never a clean
      result. The record names the tool and the lockfiles it reads and
      prescribes no command line, so there is no argv to declare and a
      `kind: command` route would have to invent one.
---

# Known vulnerabilities

CVEs / advisories affecting the *pinned/resolved* versions, with the fixed version if one exists.

## Severity

**Critical** - a High/Critical CVE with a fix available.

**Important** - a Medium CVE.

**Minor** - a dev-only CVE not shipped to users.

## Fix

Bump/pin to a fixed version; regenerate the lock (`uv lock` / equivalent) and re-run tests.

## Review lens

**Advisory accuracy** - correct advisory id, affected range, and fixed version; no stale or false-positive advisories. On the JavaScript side the id is a GHSA and a corresponding CVE may not exist, so report the GHSA rather than inventing a CVE for it or dropping the advisory for want of one. pnpm 11 made this explicit by replacing `auditConfig.ignoreCves` with `ignoreGhsas`.

**Dependency attribution** - direct vs transitive attribution is right; a transitive-only finding isn't pinned as if it were direct.
