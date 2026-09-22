---
id: security/injection
domain: security
locality: local
handbook:
  - security-supply-chain/first-party-code-trace-a-path-from-source-to-sink
evidence: >-
  Rule id and `file:line` per hit, and beside each the source-to-sink trace that
  decides whether it is a finding: the untrusted source, the dangerous sink, and
  the path between them in the real code. **Every route here reports candidates
  rather than findings**, which is why each carries `alone_insufficient` and why
  the trace belongs to the check rather than to any one of them. A `subprocess`
  call on a hardcoded constant is not command injection, and a hit no trace was
  run over is reported as an untriaged candidate rather than as either a finding
  or a clean result. The trace answers nothing on its own: with no hit there is
  nothing to trace, so it is the confirmation step of whichever route produced
  the hit and never a way of answering the check.
routes:
  - lang: python
    kind: command
    tool: bandit
    argv: [bandit, "-r"]
    note: >-
      `bandit -r <pkg>` captures test id like `B602`, severity, confidence and
      `file:line`; record test id and `file:line` per hit. `<pkg>` is the caller's
      to resolve, so the argv stops at the flag and the package is the operand the
      record leaves open.
    alone_insufficient: >-
      A hit is a candidate until the source-to-sink trace this record's
      `evidence` states confirms it, so a clean run here is not the check
      answered.
  - lang: python
    kind: command
    tool: ruff
    argv: [ruff, check, "--select", S]
    applies_when: >-
      The project standardizes on ruff.
    note: >-
      `ruff check --select S`, the same recording per hit.
    alone_insufficient: >-
      A hit is a candidate until the source-to-sink trace this record's
      `evidence` states confirms it, so a clean run here is not the check
      answered.
  - lang: python
    kind: command
    tool: semgrep
    argv: [semgrep, "--config", p/python]
    note: >-
      `semgrep --config p/python` for dataflow-aware rules, the same recording per
      hit.
    alone_insufficient: >-
      A hit is a candidate until the source-to-sink trace this record's
      `evidence` states confirms it, so a clean run here is not the check
      answered.
  - lang: any
    kind: command
    tool: semgrep
    registry: pypi
    argv: [semgrep, scan, "--config", p/javascript, "--config", p/typescript]
    applies_when: >-
      A TypeScript partition; the Python partition's semgrep route is the
      `p/python` one above.
    note: >-
      `semgrep scan --config p/javascript --config p/typescript`, the second
      config for the TypeScript-specific rules; both are Semgrep Registry
      rulesets. Record rule id and `file:line` per hit. Semgrep is a
      Python-registry package, which is why this route is `lang: any` with the
      registry named: fetch it with `uvx semgrep` or `pipx run semgrep` whatever
      the partition's language is, and do not reach for the partition's own
      one-shot runner. An npm package named `semgrep` does exist, a 2020
      placeholder whose `latest` is `0.0.1` and which declares no `bin`, so `npx
      semgrep` does not fail cleanly: it pulls unvetted third-party code into the
      audit environment and then has nothing to run. Do not read a clean pass as
      this check answered on its own: run against a real TypeScript target,
      `p/javascript` plus `p/typescript` came to 74 rules and 0 findings across
      339 files where `eslint-plugin-security` returned 557 hits on the same tree,
      so on that target semgrep alone would have reported every check in this
      domain clean. Semgrep also reports that its scan is limited to files tracked
      by git, so an untracked file is skipped with no hit and no error. Run this
      and the ESLint route both, or say in the report which one produced the
      absence.
    alone_insufficient: >-
      A hit is a candidate until the source-to-sink trace this record's
      `evidence` states confirms it, so a clean run here is not the check
      answered.
  - lang: typescript
    kind: procedure
    tool: eslint
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
    alone_insufficient: >-
      A hit is a candidate until the source-to-sink trace this record's
      `evidence` states confirms it, so a clean run here is not the check
      answered.
  - lang: typescript
    kind: procedure
    tool: eslint
    needs: target-execution
    note: >-
      ESLint under the target's own flat config, which is what the grant buys: the
      project's own rule selection, with `eslint-plugin-security` where the
      project loads it. It is the same tool as the route above and a different
      invocation mode, which is the whole distinction between them; the tier is
      the only machine-readable thing that tells the modes apart, and the untiered
      route above is the one that keeps this record answering when the grant is
      withheld.
    alone_insufficient: >-
      A hit is a candidate until the source-to-sink trace this record's
      `evidence` states confirms it, so a clean run here is not the check
      answered.
  - lang: typescript
    kind: procedure
    note: >-
      TypeScript rules and greps for this check: `detect-object-injection`,
      `detect-disable-mustache-escape`, `detect-non-literal-regexp` and
      `detect-unsafe-regex`. Grep for template-interpolated SQL, `innerHTML =` and
      `dangerouslySetInnerHTML`, and read each hit. `detect-object-injection` in
      particular fires on ordinary dynamic property access, so it is the rule most
      likely to produce volume without findings.
    alone_insufficient: >-
      A hit is a candidate until the source-to-sink trace this record's
      `evidence` states confirms it, so a clean run here is not the check
      answered.
---

# Injection

Command, SQL (string-built queries), path traversal (`../` into file ops), template/SSTI, and SSRF (user-controlled URL into an outbound request).

## Severity

**Critical** - a confirmed exploitable path from untrusted input to code execution / injection (RCE, SQLi, command injection) on a reachable surface.

**Important** - an injection/deserialization on a surface not clearly attacker-reachable but plausible.

**Minor** - a defense-in-depth gap, a low-confidence scanner hit that survives review only as a code-smell.

## Fix

**Neutralize the sink:** parameterized queries instead of string SQL; `subprocess.run([...])` with an argument list and no `shell=True`.

**Validate/canonicalize input at the boundary:** allowlist, path canonicalization + containment check (defeat traversal), URL host allowlisting (defeat SSRF).

## Review lens

**Exploitability** - is each Critical/Important finding a genuinely reachable source→sink path, or a scanner artifact? Does each fix actually cut the path (not just silence the linter)?

**No security regression** - the fix does not open a new hole (e.g. an allowlist that is trivially bypassable).
