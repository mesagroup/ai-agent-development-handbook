---
id: security/unsafe-io
domain: security
locality: local
handbook:
  - security-supply-chain/first-party-code-trace-a-path-from-source-to-sink
tooling:
  python: [bandit, ruff, semgrep]
  typescript: [semgrep, eslint, eslint-plugin-security]
needs:
  target-execution: [eslint, eslint-plugin-security]
---

# Unsafe I/O & deserialization

XML from untrusted source (XXE via `xml.etree`/`lxml`), tarfile/zip extraction without path checks (zip-slip), world-writable temp files, following symlinks.

## Severity

**Important** - an injection/deserialization on a surface not clearly attacker-reachable but plausible.

**Minor** - a defense-in-depth gap, a low-confidence scanner hit that survives review only as a code-smell.

## Tooling fallback

**Python** - `bandit -r <pkg>` (captures test id like `B602`, severity, confidence, `file:line`), or `ruff check --select S` if the project standardizes on ruff, or `semgrep --config p/python` for dataflow-aware rules. Record test id + `file:line` per hit.

**TypeScript** - `semgrep scan --config p/javascript` (add `--config p/typescript` for the TypeScript-specific rules; both are Semgrep Registry rulesets), or ESLint with `eslint-plugin-security`, whose `recommended` flat config turns on the `detect-*` rules. Record rule id + `file:line` per hit. Semgrep is not an npm package, so fetch it with `uvx` or `pipx`; the partition's own one-shot runner will not find it, and an attempt that fails that way is indistinguishable from a missing tool. ESLint is normally the target's own dependency and runs under the target's flat config; because `eslint-plugin-security`'s rules need no type information, it can also run under an audit-owned flat config with `--config` and `--no-config-lookup` and a parser fetched alongside ESLint, which is what makes it answerable without the target's `node_modules`. What the target's own config buys is the project's own rule selection. Triage every hit by reading it: the plugin's own documentation warns it "finds a lot of false positives which need triage by a human", so an untriaged hit list is not a finding list.

**TypeScript rules and greps for this check** - `detect-non-literal-fs-filename`. Grep for `path.join(` and the `fs` read and write calls where any component derives from a request, and for `..` traversal, and read each hit.

## Fix

**Neutralize the sink:** `defusedxml` for untrusted XML.

**Validate/canonicalize input at the boundary:** path canonicalization + containment check (defeat zip-slip).

## Review lens

**Exploitability** - is each Critical/Important finding a genuinely reachable source→sink path, or a scanner artifact? Does each fix actually cut the path (not just silence the linter)?

**No security regression** - the fix does not open a new hole (e.g. an allowlist that is trivially bypassable).
