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
tooling:
  python: [bandit, ruff, semgrep]
  typescript: [semgrep, eslint, eslint-plugin-security]
needs:
  target-execution: [eslint, eslint-plugin-security]
---

# Crypto & randomness

Weak hashes for security use (`md5`/`sha1`), `random` used where `secrets` is required (tokens, salts), disabled TLS verification (`verify=False`), hardcoded IV/keys.

## Severity

**Important** - disabled TLS verification; weak crypto protecting real secrets.

**Minor** - an insecure-randomness use with no security impact, a low-confidence scanner hit that survives review only as a code-smell.

## Tooling fallback

**Python** - `bandit -r <pkg>` (captures test id like `B602`, severity, confidence, `file:line`), or `ruff check --select S` if the project standardizes on ruff, or `semgrep --config p/python` for dataflow-aware rules. Record test id + `file:line` per hit. Grep the codebase for these patterns even where the scanner is silent (`verify=False`, `md5(`), and read each hit.

**TypeScript** - `semgrep scan --config p/javascript` (add `--config p/typescript` for the TypeScript-specific rules; both are Semgrep Registry rulesets), or ESLint with `eslint-plugin-security`, whose `recommended` flat config turns on the `detect-*` rules. Record rule id + `file:line` per hit. Semgrep is a Python-registry package, so fetch it with `uvx semgrep` or `pipx run semgrep` whatever the partition's language is, and do not reach for the partition's own one-shot runner: an npm package named `semgrep` does exist - a 2020 placeholder whose `latest` is `0.0.1` and which declares no `bin` - so `npx semgrep` does not fail cleanly, it pulls unvetted third-party code into the audit environment and then has nothing to run. ESLint is normally the target's own dependency and runs under the target's flat config; because `eslint-plugin-security`'s rules need no type information, it can also run under an audit-owned flat config with `--config` and `--no-config-lookup` and a parser fetched alongside ESLint, which is what makes it answerable without the target's `node_modules`. What the target's own config buys is the project's own rule selection. Triage every hit by reading it: the plugin's own documentation warns it "finds a lot of false positives which need triage by a human", so an untriaged hit list is not a finding list.

**TypeScript rules and greps for this check** - `detect-pseudoRandomBytes` and `detect-possible-timing-attacks` are the plugin rules that bear on crypto and randomness. Grep for `createHash('md5')`, `createHash('sha1')`, `Math.random()` wherever the value is token-shaped, and `rejectUnauthorized: false`, and read each hit: `Math.random()` picking a UI jitter is not a weak token.

## Fix

**Neutralize the sink:** `secrets` for tokens; restore TLS verification.
