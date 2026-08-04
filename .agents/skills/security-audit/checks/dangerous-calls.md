---
id: security/dangerous-calls
domain: security
locality: local
handbook:
  - security-supply-chain/first-party-code-trace-a-path-from-source-to-sink
tooling:
  python: [bandit, ruff, semgrep]
---

# Dangerous calls / code execution

`eval`, `exec`, `compile` on dynamic input; `pickle` / `marshal` / `shelve` loads of untrusted data; `yaml.load` without `SafeLoader`; `subprocess`/`os.system` with `shell=True` or an interpolated command.

## Severity

**Critical** - a confirmed exploitable path from untrusted input to code execution / injection (RCE, SQLi, command injection) on a reachable surface.

**Minor** - a dangerous pattern on trusted-only input, a low-confidence scanner hit that survives review only as a code-smell.

## Tooling fallback

**Python** - `bandit -r <pkg>` (captures test id like `B602`, severity, confidence, `file:line`), or `ruff check --select S` if the project standardizes on ruff, or `semgrep --config p/python` for dataflow-aware rules. Record test id + `file:line` per hit.

Grep the codebase for these patterns even where the scanner is silent (`eval(`, `pickle.load`, `yaml.load(`, `shell=True`, `os.system`, `subprocess.*(f"`), and read each hit.

## Fix

**Neutralize the sink:** `subprocess.run([...])` with an argument list and no `shell=True`; `yaml.safe_load`; `json`/a schema-validated format instead of `pickle`.

## Review lens

**Exploitability** - is each Critical/Important finding a genuinely reachable source→sink path, or a scanner artifact? Does each fix actually cut the path (not just silence the linter)?
