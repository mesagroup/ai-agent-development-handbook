---
id: security/injection
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

# Injection

Command, SQL (string-built queries), path traversal (`../` into file ops), template/SSTI, and SSRF (user-controlled URL into an outbound request).

## Severity

**Critical** - a confirmed exploitable path from untrusted input to code execution / injection (RCE, SQLi, command injection) on a reachable surface.

**Important** - an injection/deserialization on a surface not clearly attacker-reachable but plausible.

**Minor** - a defense-in-depth gap, a low-confidence scanner hit that survives review only as a code-smell.

## Tooling fallback

**Python** - `bandit -r <pkg>` (captures test id like `B602`, severity, confidence, `file:line`), or `ruff check --select S` if the project standardizes on ruff, or `semgrep --config p/python` for dataflow-aware rules. Record test id + `file:line` per hit.

**TypeScript** - `semgrep scan --config p/javascript` (add `--config p/typescript` for the TypeScript-specific rules; both are Semgrep Registry rulesets), or ESLint with `eslint-plugin-security`, whose `recommended` flat config turns on the `detect-*` rules. Record rule id + `file:line` per hit. Semgrep is a Python-registry package, so fetch it with `uvx semgrep` or `pipx run semgrep` whatever the partition's language is, and do not reach for the partition's own one-shot runner: an npm package named `semgrep` does exist - a 2020 placeholder whose `latest` is `0.0.1` and which declares no `bin` - so `npx semgrep` does not fail cleanly, it pulls unvetted third-party code into the audit environment and then has nothing to run. ESLint is normally the target's own dependency and runs under the target's flat config; because `eslint-plugin-security`'s rules need no type information, it can also run under an audit-owned flat config with `--config` and `--no-config-lookup` and a parser fetched alongside ESLint, which is what makes it answerable without the target's `node_modules`. What the target's own config buys is the project's own rule selection. Triage every hit by reading it: the plugin's own documentation warns it "finds a lot of false positives which need triage by a human", so an untriaged hit list is not a finding list.

**TypeScript rules and greps for this check** - `detect-object-injection`, `detect-disable-mustache-escape`, `detect-non-literal-regexp` and `detect-unsafe-regex`. Grep for template-interpolated SQL, `innerHTML =` and `dangerouslySetInnerHTML`, and read each hit. `detect-object-injection` in particular fires on ordinary dynamic property access, so it is the rule most likely to produce volume without findings.

**Dataflow verification (the load-bearing step):** for each scanner hit, trace source → sink in the real code to confirm an attacker-reachable path and rule out false positives (a `subprocess` call on a hardcoded constant is not command injection). This is what separates a real finding from a scanner artifact.

## Fix

**Neutralize the sink:** parameterized queries instead of string SQL; `subprocess.run([...])` with an argument list and no `shell=True`.

**Validate/canonicalize input at the boundary:** allowlist, path canonicalization + containment check (defeat traversal), URL host allowlisting (defeat SSRF).

## Review lens

**Exploitability** - is each Critical/Important finding a genuinely reachable source→sink path, or a scanner artifact? Does each fix actually cut the path (not just silence the linter)?

**No security regression** - the fix does not open a new hole (e.g. an allowlist that is trivially bypassable).
