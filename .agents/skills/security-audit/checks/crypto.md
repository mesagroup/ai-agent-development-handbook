---
id: security/crypto
domain: security
locality: local
handbook: []
handbook_note: >-
  The handbook's own sink taxonomy (shell/subprocess, eval/exec,
  deserialization, SQL, filesystem paths, outbound requests, template
  rendering) names no crypto or randomness sink, and its secrets clause
  covers what a credential must not be, not how it is hashed, generated, or
  transmitted - so no clause grounds a dedicated crypto & randomness check.
routes:
  - lang: python
    kind: command
    tool: bandit
    argv: [bandit, "-r"]
    note: >-
      `bandit -r <pkg>` captures test id like `B602`, severity, confidence and
      `file:line`; record test id and `file:line` per hit. `<pkg>` is the caller's
      to resolve, so the argv stops at the flag and the package is the operand the
      record leaves open. Grep the codebase for `verify=False` and `md5(` even
      where the scanner is silent, and read each hit.
  - lang: python
    kind: command
    tool: ruff
    argv: [ruff, check, "--select", S]
    note: >-
      `ruff check --select S` where the project standardizes on ruff: the `S`
      ruleset is bandit's rules carried by ruff, so a hit is recorded and triaged
      the same way.
  - lang: python
    kind: command
    tool: semgrep
    argv: [semgrep, "--config", p/python]
    note: >-
      `semgrep --config p/python` for dataflow-aware rules, where a scanner that
      follows a value from source to sink is worth the fetch.
  - lang: any
    kind: command
    tool: semgrep
    registry: pypi
    argv: [semgrep, scan, "--config", p/javascript]
    applies_when: >-
      A TypeScript or JavaScript partition; the Python partition's semgrep route
      is the `p/python` one above.
    note: >-
      `semgrep scan --config p/javascript`, with `--config p/typescript` added for
      the TypeScript-specific rules; both are Semgrep Registry rulesets. Record
      rule id and `file:line` per hit. Semgrep is a Python-registry package, which
      is why this route is `lang: any` with the registry named: fetch it with `uvx
      semgrep` or `pipx run semgrep` whatever the partition's language is, and do
      not reach for the partition's own one-shot runner. An npm package named
      `semgrep` does exist, a 2020 placeholder whose `latest` is `0.0.1` and which
      declares no `bin`, so `npx semgrep` does not fail cleanly: it pulls unvetted
      third-party code into the audit environment and then has nothing to run. Do
      not read a clean pass as this check answered on its own: run against a real
      TypeScript target, `p/javascript` plus `p/typescript` came to 74 rules and 0
      findings across 339 files where `eslint-plugin-security` returned 557 hits
      on the same tree, so on that target semgrep alone would have reported every
      check in this domain clean. Semgrep also reports that its scan is limited to
      files tracked by git, so an untracked file is skipped with no hit and no
      error. Run this and the ESLint route both, or say in the report which one
      produced the absence.
  - lang: typescript
    kind: procedure
    tool: eslint-plugin-security
    note: >-
      ESLint with `eslint-plugin-security`, whose `recommended` flat config turns
      on the `detect-*` rules, run under a flat config the audit supplies rather
      than the target's: pointed at an audit-owned config with `--config` and
      `--no-config-lookup`, the plugin's rules need no type information, so they
      read the target's source without loading the target's own flat config and no
      `node_modules` is needed. This is the invocation that answers under a
      withheld grant, and the reason the route carries no tier: what the install
      needs is network rather than the target's tree. Install ESLint, the parser
      and the plugin into an audit-owned directory and keep the config in it,
      rather than fetching them with a one-shot runner: node resolves a flat
      config's imports from where the config file lives, so a config outside the
      runner's sandbox aborts with `ERR_MODULE_NOT_FOUND: Cannot find package
      '@typescript-eslint/parser'` before any rule runs. Do not read the exit code
      as the verdict: the target's own `eslint-disable` comments name rules an
      audit-owned config does not load, and ESLint reports each as an
      error-severity `Definition for rule 'X' was not found`, so a pass whose
      every real hit was a warning still exits 1; on the run this was observed on,
      19 such errors against 557 findings. Record rule id and `file:line` per hit,
      and triage every hit by reading it: the plugin's own documentation warns it
      finds a lot of false positives which need triage by a human, so an untriaged
      hit list is not a finding list. A withheld grant is not a reason to drop to
      Semgrep alone: reaching for `semgrep` because it carries no tier, and
      stopping there, is how this check reports a clean result on the evidence the
      semgrep route records. The record names the flags in a sentence and
      prescribes no command line, and `--config` takes a path the record names no
      value for, so there is no argv to declare.
  - lang: typescript
    kind: procedure
    tool: eslint-plugin-security
    needs: target-execution
    note: >-
      The same plugin under the target's own flat config, which is what the grant
      buys: the project's own rule selection. That config loads its plugins from
      the target's own `node_modules`, and without it ESLint aborts with
      `ERR_MODULE_NOT_FOUND` rather than reporting a hit. It is the same tool as
      the route above and a different invocation mode, which is the whole
      distinction between them; the tier is the only machine-readable thing that
      tells the modes apart, and the untiered route above is the one that keeps
      this record answering when the grant is withheld.
  - lang: typescript
    kind: procedure
    note: >-
      TypeScript rules and greps for this check: `detect-pseudoRandomBytes` and
      `detect-possible-timing-attacks` are the plugin rules that bear on crypto
      and randomness. Grep for `createHash('md5')`, `createHash('sha1')`,
      `Math.random()` wherever the value is token-shaped, and `rejectUnauthorized:
      false`, and read each hit: `Math.random()` picking a UI jitter is not a weak
      token.
---

# Crypto & randomness

Weak hashes for security use (`md5`/`sha1`), `random` used where `secrets` is required (tokens, salts), disabled TLS verification (`verify=False`), hardcoded IV/keys.

## Severity

**Important** - disabled TLS verification; weak crypto protecting real secrets.

**Minor** - an insecure-randomness use with no security impact, a low-confidence scanner hit that survives review only as a code-smell.

## Fix

**Neutralize the sink:** `secrets` for tokens; restore TLS verification.
