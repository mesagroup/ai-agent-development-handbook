---
id: security/dangerous-calls
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

# Dangerous calls / code execution

`eval`, `exec`, `compile` on dynamic input; `pickle` / `marshal` / `shelve` loads of untrusted data; `yaml.load` without `SafeLoader`; `subprocess`/`os.system` with `shell=True` or an interpolated command.

## Severity

**Critical** - a confirmed exploitable path from untrusted input to code execution / injection (RCE, SQLi, command injection) on a reachable surface.

**Minor** - a dangerous pattern on trusted-only input, a low-confidence scanner hit that survives review only as a code-smell.

## Tooling fallback

**Python** - `bandit -r <pkg>` (captures test id like `B602`, severity, confidence, `file:line`), or `ruff check --select S` if the project standardizes on ruff, or `semgrep --config p/python` for dataflow-aware rules. Record test id + `file:line` per hit. Grep the codebase for these patterns even where the scanner is silent (`eval(`, `pickle.load`, `yaml.load(`, `shell=True`, `os.system`, `subprocess.*(f"`), and read each hit.

**TypeScript** - `semgrep scan --config p/javascript` (add `--config p/typescript` for the TypeScript-specific rules; both are Semgrep Registry rulesets), or ESLint with `eslint-plugin-security`, whose `recommended` flat config turns on the `detect-*` rules. Record rule id + `file:line` per hit. Semgrep is a Python-registry package, so fetch it with `uvx semgrep` or `pipx run semgrep` whatever the partition's language is, and do not reach for the partition's own one-shot runner: an npm package named `semgrep` does exist - a 2020 placeholder whose `latest` is `0.0.1` and which declares no `bin` - so `npx semgrep` does not fail cleanly, it pulls unvetted third-party code into the audit environment and then has nothing to run. ESLint is normally the target's own dependency and runs under the target's flat config; because `eslint-plugin-security`'s rules need no type information, it can also run under an audit-owned flat config with `--config` and `--no-config-lookup` and a parser fetched alongside ESLint, which is what makes it answerable without the target's `node_modules`. What the target's own config buys is the project's own rule selection. Triage every hit by reading it: the plugin's own documentation warns it "finds a lot of false positives which need triage by a human", so an untriaged hit list is not a finding list.

**TypeScript rules and greps for this check** - `detect-child-process`, `detect-eval-with-expression`, `detect-non-literal-require`, `detect-new-buffer` and `detect-buffer-noassert`. Grep for `eval(`, `new Function(`, `child_process.exec(`, `execSync(`, `vm.runInNewContext` and `require(` on anything that is not a literal, and read each hit.

## Fix

**Neutralize the sink:** `subprocess.run([...])` with an argument list and no `shell=True`; `yaml.safe_load`; `json`/a schema-validated format instead of `pickle`.

## Review lens

**Exploitability** - is each Critical/Important finding a genuinely reachable source→sink path, or a scanner artifact? Does each fix actually cut the path (not just silence the linter)?
