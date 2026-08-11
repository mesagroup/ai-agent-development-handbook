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

**TypeScript** - `semgrep scan --config p/javascript` (add `--config p/typescript` for the TypeScript-specific rules; both are Semgrep Registry rulesets), or ESLint with `eslint-plugin-security`, whose `recommended` flat config turns on the `detect-*` rules. Record rule id + `file:line` per hit. Semgrep is a Python-registry package, so fetch it with `uvx semgrep` or `pipx run semgrep` whatever the partition's language is, and do not reach for the partition's own one-shot runner: an npm package named `semgrep` does exist - a 2020 placeholder whose `latest` is `0.0.1` and which declares no `bin` - so `npx semgrep` does not fail cleanly, it pulls unvetted third-party code into the audit environment and then has nothing to run. Do not read a clean `semgrep` pass as this check answered on its own: run against a real TypeScript target, `p/javascript` plus `p/typescript` came to **74 rules and 0 findings** across 339 files where `eslint-plugin-security` returned 557 hits on the same tree, so on that target semgrep alone would have reported every check in this domain clean. Semgrep also reports that its scan is **limited to files tracked by git**, so an untracked file is skipped with no hit and no error. Run both lenses, or say in the report which one produced the absence. **A withheld grant is not a reason to drop to Semgrep alone here.** This record tiers `eslint` and `eslint-plugin-security` at `target-execution` for the invocation that loads the *target's* flat config out of its `node_modules`; the audit-owned install described above is a different invocation of the same tools that needs nothing from the target, so it runs under no grant and the engine's preference for an untiered tool does not reach it. Reaching for `semgrep` because it carries no tier, and stopping there, is how this check reports a clean result on the evidence the run above shows it produces. ESLint is normally the target's own dependency and runs under the target's flat config; because `eslint-plugin-security`'s rules need no type information, it can also run under an audit-owned flat config with `--config` and `--no-config-lookup`, which is what makes it answerable without the target's `node_modules`. **Install ESLint, the parser and the plugin into an audit-owned directory and keep the config in it**, rather than fetching them with a one-shot runner: node resolves a flat config's imports from where the config file lives, so a config outside the runner's sandbox aborts with `ERR_MODULE_NOT_FOUND: Cannot find package '@typescript-eslint/parser'` before any rule runs. What that install needs is network rather than the target's tree, so the ungranted answer stands. **And do not read the exit code as the verdict here**: the target's own `eslint-disable` comments name rules an audit-owned config does not load, and ESLint reports each as an error-severity `Definition for rule 'X' was not found`, so a pass whose every real hit was a warning still exits 1 - on the run this was observed on, 19 such errors against 557 findings. What the target's own config buys is the project's own rule selection. Triage every hit by reading it: the plugin's own documentation warns it "finds a lot of false positives which need triage by a human", so an untriaged hit list is not a finding list.

**TypeScript rules and greps for this check** - `detect-pseudoRandomBytes` and `detect-possible-timing-attacks` are the plugin rules that bear on crypto and randomness. Grep for `createHash('md5')`, `createHash('sha1')`, `Math.random()` wherever the value is token-shaped, and `rejectUnauthorized: false`, and read each hit: `Math.random()` picking a UI jitter is not a weak token.

## Fix

**Neutralize the sink:** `secrets` for tokens; restore TLS verification.
