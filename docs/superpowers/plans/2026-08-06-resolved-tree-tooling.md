# Resolved-tree tooling policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the `*-audit` family a way to say what a tool needs *present in the target* before it can answer, a policy for obtaining it that never writes into the target, and a `no-evidence` reason that tells "not permitted" from "would not install".

**Architecture:** A per-tool tier (`resolved-tree`, `target-execution`) recorded in a new optional `needs:` frontmatter key and validated against the record's existing `tooling:` map, so a rename fails the gate. Two default-off grants resolved at scope time and carried in the fan-out payload. Under a grant the tree is reconstructed in a scratch directory outside `target_root`; the target is never installed into.

**Tech Stack:** Python 3 + PyYAML (`scripts/audit_checks.py`), pytest, ruff. The rest is Markdown: skill prompts under `.agents/skills/`, records under `.agents/skills/<domain>-audit/checks/`, and the audit standing records under `docs/audit/`.

**Spec:** `docs/superpowers/specs/2026-08-06-resolved-tree-tooling-design.md`. Read it before starting; every decision below is numbered against it.

## Global Constraints

Copied from the spec and from `CLAUDE.md`. Every task's requirements implicitly include this section.

- Run Python via `uv run`. Never invoke `python` or `pytest` directly.
- Before every commit: `uv run ruff check . && uv run ruff format --check .` and `uv run pytest tests/ -q` and `uv run python scripts/render_handbook_traceability.py --check`. All three must be clean.
- Markdown is never hard-wrapped: one paragraph is one source line. Never reflow a line you did not change.
- No em-dash (U+2014) in `docs/engineering/`, `docs/superpowers/specs/`, `docs/superpowers/plans/`. Use ` - `. Files under `docs/audit/` and `CLAUDE.md` do use em-dashes; match the file you are in.
- Every commit message ends with `Refs #19`. No Claude credits in commit messages.
- A commit touching an LLM/agentic prompt (anything under `.agents/skills/`) must say WHY, not just what, and prompt changes go in their own commit, separate from code.
- Never assert a count you did not compute. Name a thing, don't number it. Avoid claims about a sibling record unless you verified it as you wrote.
- Handbook and skill links to files in this repo are absolute GitHub URLs under `https://github.com/mesagroup/ai-agent-development-handbook/blob/main/`, because the skills run from a plugin cache in other repositories where a relative path resolves to nothing.
- Never commit environment-specific values: absolute personal paths, profile names, tokens, hostnames, emails.
- Stage explicit paths with `git add <path>`. Never `git add -A`, `git add .`, or `git commit -a`.

## The tier vocabulary

Three tiers. The first has no name, because most tools are in it and an unmarked record must mean the ordinary thing.

| Tier | The tool needs |
|---|---|
| *(default, unnamed - absent from `needs:`)* | Only what a read-only clone contains: source, manifests, lockfiles |
| `resolved-tree` | The dependency graph materialized, so package metadata can be read |
| `target-execution` | The tree, and running the target's own code |

`target-execution` implies `resolved-tree`. A tool that *runs* without the tree but silently returns a wrong, empty or partial answer is `resolved-tree`, not default: the whole point of the axis is that a quiet wrong answer is worse than a loud failure.

**A tier describes the invocation the record prescribes, not the tool in the abstract.** Several tools straddle the boundary by subcommand or flag - `npm sbom` needs the tree by default and reads the lockfile under `--package-lock-only`, `pip-audit` audits whatever environment it is launched from unless given `--locked` or `-r`, `cyclonedx-py environment` reads an installed environment where its `requirements` and `poetry` subcommands parse files. A record naming one of these must pin the mode in its `## Tooling fallback`, and is then classified by the mode it pinned. Leaving the mode unpinned and the tier absent is the worst of both: the frontmatter promises a tool that runs on a clone and the prose sends an agent to the invocation that does not.

The classifications below were verified against each tool's own documentation, and the JavaScript ones additionally reproduced on a two-file fixture run with and without `node_modules`. Do not re-derive them from general knowledge while implementing; where a verdict looks wrong, check the tool's docs and change the plan.

## File structure

| File | Responsibility |
|---|---|
| `scripts/audit_checks.py` | Owns the `needs:` schema and its intra-record validation, alongside the existing fields |
| `tests/scripts/test_audit_checks.py` | Per-rule unit tests, plus the two family-wide convention tests |
| `tests/scripts/test_render_handbook_traceability.py` | Its `_check` fixture constructs a `Check` directly and must gain the new field |
| `.agents/skills/<domain>-audit/checks/*.md` | Each record classifies its own tools and explains the consequence in `## Tooling fallback` |
| `.agents/skills/audit-core/SKILL.md` | The engine: the tier axis, the two grants, reconstruct-outside, the `no-evidence` reasons |
| `.agents/skills/audit/SKILL.md` | The sweep: grants resolved at step 0, carried in the fan-out, rendered in the report template |
| `docs/audit/sweep-obligations.md` | A row per obligation this change adds to the engine |
| `CLAUDE.md` | The check-records paragraph gains `needs:` |

---

### Task 1: The `needs:` field in the loader

Spec decision 7. Nothing else in the plan works until a record can carry the key without the gate rejecting it as an unknown frontmatter field.

**Files:**
- Modify: `scripts/audit_checks.py`
- Modify: `tests/scripts/test_audit_checks.py`
- Modify: `tests/scripts/test_render_handbook_traceability.py:118-128`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `audit_checks.NEEDS_TIERS: tuple[str, ...]` equal to `("resolved-tree", "target-execution")`, and `Check.needs: dict[str, tuple[str, ...]]` mapping a tier to the tool names in it. A record with no `needs:` key gets `{}`. Later tasks read `check.needs` and `check.tooling`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/scripts/test_audit_checks.py`, after `test_optin_and_empty_handbook_with_note_are_valid`:

```python
NEEDS = """---
id: deps/hygiene
domain: deps
locality: global
handbook:
  - security-supply-chain/depend-only-on-what-you-can-account-for-a
tooling:
  python: [deptry]
  typescript: [depcheck, knip]
needs:
  resolved-tree: [deptry, knip]
---

# Hygiene

Declared-but-unused dependencies.

## Tooling fallback

`depcheck` answers from source alone; `knip` and `deptry` need the tree.
"""


def test_needs_records_the_tier_of_each_tool(tmp_path):
    _write(tmp_path, "deps-audit/checks/hygiene.md", NEEDS)
    checks, errors = ac.load_checks(tmp_path)
    assert errors == []
    assert checks["deps/hygiene"].needs == {"resolved-tree": ("deptry", "knip")}


def test_a_record_without_needs_claims_every_tool_runs_on_a_clone(tmp_path):
    _write(tmp_path, "arch-audit/checks/layering.md", GOOD)
    checks, errors = ac.load_checks(tmp_path)
    assert errors == []
    assert checks["arch/layering"].needs == {}


def test_needs_must_name_a_known_tier(tmp_path):
    _write(
        tmp_path,
        "deps-audit/checks/hygiene.md",
        NEEDS.replace("resolved-tree: [deptry, knip]", "needs-network: [deptry]"),
    )
    _, errors = ac.load_checks(tmp_path)
    assert any("needs-network" in e and "must map one of" in e for e in errors)


def test_needs_must_name_a_tool_the_record_offers(tmp_path):
    _write(
        tmp_path,
        "deps-audit/checks/hygiene.md",
        NEEDS.replace("[deptry, knip]", "[deptry, kn1p]"),
    )
    _, errors = ac.load_checks(tmp_path)
    assert any(
        "'kn1p'" in e and "not in this record's tooling" in e for e in errors
    )


def test_a_tool_may_not_sit_in_two_tiers(tmp_path):
    _write(
        tmp_path,
        "deps-audit/checks/hygiene.md",
        NEEDS.replace(
            "  resolved-tree: [deptry, knip]",
            "  resolved-tree: [deptry, knip]\n  target-execution: [knip]",
        ),
    )
    _, errors = ac.load_checks(tmp_path)
    assert any(
        "'knip'" in e and "resolved-tree" in e and "target-execution" in e
        for e in errors
    )


def test_needs_without_tooling_is_an_error(tmp_path):
    _write(
        tmp_path,
        "deps-audit/checks/hygiene.md",
        NEEDS.replace("tooling:\n  python: [deptry]\n  typescript: [depcheck, knip]\n", ""),
    )
    _, errors = ac.load_checks(tmp_path)
    assert any("does not declare" in e for e in errors)


def test_needs_must_be_a_mapping(tmp_path):
    _write(
        tmp_path,
        "deps-audit/checks/hygiene.md",
        NEEDS.replace("needs:\n  resolved-tree: [deptry, knip]", "needs: [deptry]"),
    )
    _, errors = ac.load_checks(tmp_path)
    assert any("needs must be a mapping" in e for e in errors)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/scripts/test_audit_checks.py -q -k needs`

Expected: FAIL. The first several report `unknown frontmatter key 'needs'`; `test_needs_records_the_tier_of_each_tool` additionally fails on `AttributeError: 'Check' object has no attribute 'needs'`.

- [ ] **Step 3: Add the field to the loader**

In `scripts/audit_checks.py`, add the tier tuple beside `LOCALITIES` and extend `FIELDS`:

```python
LOCALITIES = ("local", "global")
# What a tool needs *present in the target* before it can answer, which is a
# different axis from where the tool comes from: a registry package a runner
# can fetch may still need the tree, and a standalone binary no runner can
# fetch may answer from a lockfile alone. `target-execution` implies
# `resolved-tree`. The common case carries no tier and no key.
NEEDS_TIERS = ("resolved-tree", "target-execution")
FIELDS = frozenset(
    {
        "id",
        "domain",
        "locality",
        "handbook",
        "handbook_note",
        "tooling",
        "needs",
        "optin",
    }
)
```

Add the field to the dataclass, after `tooling`:

```python
    tooling: dict[str, tuple[str, ...]]
    needs: dict[str, tuple[str, ...]]
    optin: bool
```

In `_load_one`, insert this block between the `tooling` block and the `optin` block:

```python
    needs: dict[str, tuple[str, ...]] = {}
    raw_needs = meta.get("needs")
    if raw_needs is not None:
        if not isinstance(raw_needs, dict):
            errors.append(f"{where}: needs must be a mapping of tier to tool list")
        elif raw_tooling is None:
            errors.append(
                f"{where}: needs classifies tooling this record does not declare - "
                "add a tooling map, or drop needs"
            )
        else:
            offered = {name for names in tooling.values() for name in names}
            tier_of: dict[str, str] = {}
            for tier, tools in raw_needs.items():
                names = _str_list(tools)
                if tier not in NEEDS_TIERS or names is None:
                    errors.append(
                        f"{where}: needs[{tier!r}] must map one of {NEEDS_TIERS} to "
                        "a list of tool-name strings"
                    )
                    continue
                for name in names:
                    if name not in offered:
                        errors.append(
                            f"{where}: needs[{tier}] names {name!r}, which is not in "
                            "this record's tooling"
                        )
                    if name in tier_of:
                        errors.append(
                            f"{where}: {name!r} is classified both "
                            f"{tier_of[name]} and {tier}"
                        )
                    else:
                        tier_of[name] = tier
                needs[tier] = names
```

Pass it to the constructor, after `tooling=tooling,`:

```python
            needs=needs,
```

- [ ] **Step 4: Update the module docstring**

In the frontmatter table in the docstring, add a row after the `tooling` row:

```
| `needs` | no | Tier to tool names, for tools needing more than a read-only clone |
```

And add this paragraph immediately after the paragraph that begins "A `tooling` value is a list of names, not of invocations":

```
`needs` answers a different question about the same names: not where the
tool comes from, but what must be present in the target before it can
answer. A tool absent from `needs` runs against a read-only clone;
`resolved-tree` needs the dependency graph materialized; `target-execution`
needs that and runs the target's own code. The names are deliberately
repeated from `tooling` rather than folded into it, and the repetition is
what is checked: every name under `needs` must be one the record actually
offers, so a rename that misses one of the two places fails here instead of
quietly describing a tool that is no longer listed.
```

- [ ] **Step 5: Update the direct `Check` construction in the traceability tests**

`tests/scripts/test_render_handbook_traceability.py:118-128` builds a `Check` by keyword. Add `needs={}` immediately after `tooling={},`. Without this the whole traceability test module errors on a missing argument.

- [ ] **Step 6: Run the full gate**

```bash
uv run pytest tests/ -q
uv run ruff check . && uv run ruff format --check .
uv run python scripts/render_handbook_traceability.py --check
```

Expected: all pass. The integrity gate must still exit 0 - no record carries `needs:` yet, so nothing in the tree exercises the new rules.

- [ ] **Step 7: Commit**

```bash
git add scripts/audit_checks.py tests/scripts/test_audit_checks.py tests/scripts/test_render_handbook_traceability.py
git commit -m "feat: let a record say what its tools need present in the target

A tooling name already says where the tool comes from and cannot say what
must exist in the target before it answers, so a tool that needs the
dependency tree is indistinguishable from one that does not until it fails.

needs: maps a tier to tool names and is validated against tooling:, so a
rename that misses one of the two places fails the gate rather than
describing a tool the record no longer offers.

Refs #19"
```

---
### Task 2: Classify the architecture records

Nine of the eleven `arch` records name a tool that needs more than a read-only clone. `arch/martin-metrics` and `arch/size` do not and get no key.

**Files:** modify `.agents/skills/arch-audit/checks/{complexity,complexity-gate,coupling,cycles,dead-code,hidden-coupling,layering,over-abstraction,over-decomposition}.md`

**Interfaces:** consumes `NEEDS_TIERS` from Task 1. Produces the classifications Task 5's consistency test holds every other record to.

- [ ] **Step 1: Add the frontmatter key to each record**

Insert a `needs:` block immediately after the record's existing `tooling:` block. Exactly these, and nothing else:

| Record | `needs:` block |
|---|---|
| `complexity.md` | `needs:`<br>`  target-execution: [eslint, eslint-plugin-sonarjs]` |
| `complexity-gate.md` | `needs:`<br>`  target-execution: [eslint, eslint-plugin-sonarjs]` |
| `coupling.md` | `needs:`<br>`  resolved-tree: [pydeps, dependency-cruiser]` |
| `cycles.md` | `needs:`<br>`  resolved-tree: [pydeps, dependency-cruiser]` |
| `dead-code.md` | `needs:`<br>`  target-execution: [knip]` |
| `hidden-coupling.md` | `needs:`<br>`  target-execution: [eslint, knip]` |
| `layering.md` | `needs:`<br>`  resolved-tree: [dependency-cruiser]` |
| `over-abstraction.md` | `needs:`<br>`  target-execution: [knip]` |
| `over-decomposition.md` | `needs:`<br>`  resolved-tree: [dependency-cruiser]` |

- [ ] **Step 2: Say in each fallback what the classified tool does without the tree**

Each of these fails quietly rather than loudly, which is the whole reason the tier exists. Append one sentence to the relevant `## Tooling fallback` paragraph, in that record's own voice. The facts to state, verified against each tool's documentation and reproduced on a two-file fixture:

- **`dependency-cruiser`** needs a TypeScript compiler resolvable beside it and the target's dependencies present. Without the compiler it reports `totalCruised: 0` and exits 0 - an empty answer, not an error. With the compiler but no `node_modules`, every external import comes back `couldNotResolve: true` with dependency type `unknown`, which silently breaks the `not-to-unresolvable`, `not-to-dev-dep` and `no-non-package-json` rules while first-party cycle and layering edges stay correct. So a cycles or layering question can be answered read-only; a dependency-type question cannot.
- **`madge`** excludes installed dependencies by default and brings its own TypeScript through `dependency-tree`, so the first-party graph is complete without an install. It is the read-only option wherever it is listed beside `dependency-cruiser`. Say so, so an agent on an uninstalled partition reaches for it first.
- **`pydeps`** does not execute the target - it reads import opcodes from compiled bytecode - but it only sees modules the import machinery can find, so an uninstalled tree yields a silently incomplete graph rather than an error.
- **`knip`** loads and executes the target's dynamic tool configuration files to read their exported values, which is why it is `target-execution` and not merely `resolved-tree`. On an uninstalled tree it reports first-party source files as unused and imported packages as unused, which is a wrong answer at exit 0.
- **`eslint` and `eslint-plugin-sonarjs`** load a flat config that `import`s its plugins from the target's own `node_modules`; absent, ESLint aborts with `ERR_MODULE_NOT_FOUND`. `eslint-plugin-sonarjs` additionally has rules requiring type information, which needs a real TypeScript program over the installed tree.
- **`ts-prune` and `ts-morph`** need no install for syntax-level work, `ts-morph` serving its own `lib.d.ts` from memory. Note in `over-abstraction.md` that a type-aware `ts-morph` pass reaching into dependency types degrades silently without the tree, so keep the lens syntactic.

Do not reflow any line you are not editing.

- [ ] **Step 3: Gate and commit**

```bash
uv run pytest tests/ -q && uv run ruff check . && uv run ruff format --check .
uv run python scripts/render_handbook_traceability.py --check
git add .agents/skills/arch-audit/checks
git commit -m "docs: classify what the architecture tools need present

dependency-cruiser and knip both answer at exit 0 on an uninstalled tree
and both answer wrongly - dependency-cruiser reports every external import
unresolvable, knip reports imported packages as unused - so an agent that
treats a successful exit as a clean result publishes a finding set built on
an empty graph. madge and ts-prune genuinely do not need the tree, and the
records did not say which was which.

Refs #19"
```

---

### Task 3: Classify the dependency records, and fix what the classification exposes

Five `deps` records name a tool needing more than a clone. The research behind this task also found four places where the existing prose sends an agent to a tool that cannot answer, so this task corrects them rather than annotating around them.

**Files:** modify `.agents/skills/deps-audit/checks/{freshness,hygiene,inventory,licenses,transitive-licenses,vulnerabilities}.md`

- [ ] **Step 1: Add the frontmatter keys**

| Record | `needs:` block |
|---|---|
| `freshness.md` | `needs:`<br>`  resolved-tree: [uv, pip, npm outdated, pnpm outdated]` |
| `hygiene.md` | `needs:`<br>`  resolved-tree: [deptry, depcheck]`<br>`  target-execution: [knip]` |
| `licenses.md` | `needs:`<br>`  resolved-tree: [pip-licenses, pnpm licenses list, yarn licenses list]` |
| `transitive-licenses.md` | `needs:`<br>`  resolved-tree: [pip-licenses, pnpm licenses list, yarn licenses list]` |
| `vulnerabilities.md` | `needs:`<br>`  resolved-tree: [safety]` |

`inventory.md` gets no key, because the prose fix in step 5 pins both of its tools to modes that read files. That is the convention: **a tier describes the invocation the record prescribes**, so a record naming a tool with mode-dependent requirements must pin the mode.

- [ ] **Step 2: Correct `deps/hygiene` - `depcheck` is not the read-only option**

The record currently says `depcheck` "runs against the source alone", that both tools "answer from `package.json` plus the source rather than from a lockfile", and that "on a partition whose dependencies are not installed, `depcheck` is the one that answers". That is wrong, and it was reproduced: `depcheck`'s `bin` special resolves each dependency's *installed* `package.json` to learn its `bin` names, and `loadModuleData` swallows the failure and returns null metadata, so a dependency used only as a CLI in `scripts` is silently reported unused. On a fixture whose scripts are `eslint .` and `tsc -p .`, `depcheck` with no `node_modules` reported `eslint` and `typescript` as unused devDependencies; after an install it reported none. Its `eslint` special likewise `require`s the resolved shareable config and silently returns nothing on failure.

Rewrite that paragraph so it says: both tools need the tree, `depcheck` at `resolved-tree` and `knip` at `target-execution` because knip additionally executes the target's dynamic tool configs; on an uninstalled JavaScript partition this check has no tool that answers correctly and is `no-evidence (not-permitted)` rather than a clean result. Keep the Python half as it is except for noting that `deptry` must run inside the project's environment, since it reads installed distribution metadata.

- [ ] **Step 3: Correct `deps/freshness` - the preferred tools are the ones that do not work**

The record tells an agent to prefer `npm outdated` and `pnpm outdated` because they are "already installed and already pointed at the lockfile that is present". Both read *installed* state. `npm outdated` on a tree with no `node_modules` reports every production dependency as `MISSING`, and its own source drops any non-production dependency that is missing, so devDependencies vanish from the output entirely rather than being reported as outdated. `pnpm outdated` hard-errors without a lockfile and, with a lockfile but no install, treats every dependency as outdated because the installed version is undefined.

Rewrite the JavaScript/TypeScript paragraph to make `npm-check-updates` the read-only-clone option and the default on any partition the audit has not been granted a tree for, with the package-manager subcommands preferred only where the tree is present. Correct the false clause about the lockfile. In the Python paragraph, note that `uv pip list --outdated` and `pip list --outdated` both read the installed environment, and that the lockfile scan for floating pins is the part that survives without one.

- [ ] **Step 4: Correct `deps/licenses` - name the option that works read-only**

The closing paragraph asserts every option "needs the dependencies materialized ... or a registry lookup per package". Split that: `pip-licenses`, `pnpm licenses list` and `yarn licenses list` need the tree, while `@cyclonedx/cdxgen` with `FETCH_LICENSE=true` resolves licences from the lockfile over the network and is therefore the option that answers on a read-only clone. Say that it needs network rather than the tree, and that a `GITHUB_TOKEN` avoids the rate limiting its docs warn about. Keep the existing point that an empty licence field is itself a finding.

- [ ] **Step 5: Pin the modes in `deps/inventory` and `deps/vulnerabilities`**

`npm sbom` in its default mode loads the installed tree and throws `ESBOMPROBLEMS` rather than emitting a partial SBOM; `--package-lock-only` reads the lockfile instead and is what this record must prescribe. `cyclonedx-py environment` reads the installed environment, while its `requirements`, `poetry` and `pipenv` subcommands parse files; prescribe those and say the `environment` subcommand is the accurate one where a tree is available.

In `deps/vulnerabilities`, `pip-audit` with no arguments audits whatever environment it is launched from, which on a foreign target is the audit environment rather than the subject. Prescribe `pip-audit --locked .` or `pip-audit -r <requirements>`; note that `-r` provisions its own throwaway virtualenv and so needs network but not the target's tree. Add that `safety` requires authentication and is unusable in an unauthenticated audit whatever else is true, which is a separate reason from its tier.

- [ ] **Step 6: Gate and commit**

```bash
uv run pytest tests/ -q && uv run ruff check . && uv run ruff format --check .
uv run python scripts/render_handbook_traceability.py --check
git add .agents/skills/deps-audit/checks
git commit -m "docs: classify the dependency tools, and fix the advice that classifying them exposed

Writing down what each tool needs present turned up four records sending an
agent to a tool that cannot answer where it is sent.

deps/hygiene called depcheck the tool that answers on an uninstalled
partition; depcheck resolves each dependency's installed package.json to
learn its bin names and silently reports a script-only CLI dependency as
unused, reproduced on a fixture. deps/freshness preferred npm outdated and
pnpm outdated as 'already pointed at the lockfile', which they are not -
npm outdated drops missing devDependencies from its output entirely.
deps/licenses claimed every option needs the tree, burying the one that
does not. deps/inventory and deps/vulnerabilities named npm sbom,
cyclonedx-py and pip-audit unqualified, whose bare modes read an installed
environment - for pip-audit, the audit's own rather than the subject's.

Refs #19"
```

---

### Task 4: Classify the test records

Every `test` record that names a tool names one that runs the target's suite, except `test/property-based-gap`: `hypothesis` is detected by reading source for its use, not by running it.

**Files:** modify `.agents/skills/test-audit/checks/{coverage-reach,determinism,isolation,mutation,new-code-coverage}.md`

- [ ] **Step 1: Add the frontmatter keys**

| Record | `needs:` block |
|---|---|
| `coverage-reach.md` | `needs:`<br>`  target-execution: [pytest-cov, coverage.py]` |
| `determinism.md` | `needs:`<br>`  target-execution: [pytest-randomly, pytest-rerunfailures]` |
| `isolation.md` | `needs:`<br>`  target-execution: [pytest-timeout]` |
| `mutation.md` | `needs:`<br>`  target-execution: [mutmut, cosmic-ray]` |
| `new-code-coverage.md` | `needs:`<br>`  target-execution: [diff-cover]` |

`property-based-gap.md` gets no key.

- [ ] **Step 2: Give `test/mutation` a `## Tooling fallback` section**

It has none, and Task 5's test requires one from any record that classifies a tool. Add it after the `## Severity` section, stating: mutation testing runs the target's suite once per mutant, so it needs the `target-execution` grant and is the most expensive thing in the family to run; without the grant the check is `no-evidence (not-permitted)`. Where the grant exists, scope the run to the load-bearing module rather than the whole suite.

- [ ] **Step 3: State the constraint in the other four fallbacks**

Each already has a section; append the consequence. `diff-cover` is the one that needs care: its own invocation reads a coverage XML and a git diff, so it is read-only *given the artifact* - but producing the artifact runs the suite. State that, and state that where CI publishes the coverage XML as an artifact the check can be answered without the grant, which is the one route to an answer on a read-only clone.

- [ ] **Step 4: Gate and commit**

```bash
uv run pytest tests/ -q && uv run ruff check . && uv run ruff format --check .
uv run python scripts/render_handbook_traceability.py --check
git add .agents/skills/test-audit/checks
git commit -m "docs: classify the test tools as running the target's own suite

Every tool this domain names except hypothesis executes the subject's test
suite, which is the tier that needs its own grant: a repository invited us
to read it, and running its suite is not reading. Recording that is what
lets a withheld grant report as no-evidence (not-permitted) instead of the
domain looking clean because nothing ran.

test/mutation gains a fallback section it never had, since a record that
admits its tools need a grant has to say what to do without one.

Refs #19"
```

---

### Task 5: The two family-wide convention tests

Spec decision 7's honest limit: an absent `needs:` key is a positive claim, so no test can catch a record nobody classified. One thing a test *can* catch is a tool classified in one record and not in another - which is exactly what a forgotten record looks like whenever the tool appears more than once. That is the guard this task builds.

**Files:**
- Modify: `tests/scripts/test_audit_checks.py`

**Interfaces:**
- Consumes: `Check.needs` and `Check.tooling` from Task 1; every record classified by Tasks 2-4.
- Produces: nothing later tasks read.

- [ ] **Step 1: Write the failing tests**

Append to `tests/scripts/test_audit_checks.py`, beside the other family-wide convention tests:

```python
def test_a_tool_has_one_tier_across_the_family():
    """A tool needs the same thing everywhere, so two records that name it
    must agree. This is the only mechanical guard on the classification
    sweep: an absent `needs:` entry is a positive claim that the tool runs
    against a read-only clone, so a record nobody classified is
    indistinguishable from one deliberately left at the default - except
    when some *other* record classified the same tool, which is what this
    catches. If this fails, classify the tool the same way in both records
    - do not weaken the assertion.
    """
    checks, errors = ac.load_checks(ac.SKILLS_DIR)
    assert errors == []
    tier_of: dict[str, tuple[str, str]] = {}
    disagreements = []
    for check_id, check in sorted(checks.items()):
        classified = {
            name: tier for tier, names in check.needs.items() for name in names
        }
        for name in sorted({n for names in check.tooling.values() for n in names}):
            tier = classified.get(name, "")
            if name not in tier_of:
                tier_of[name] = (tier, check_id)
                continue
            seen_tier, seen_in = tier_of[name]
            if seen_tier != tier:
                disagreements.append(
                    f"{name!r}: {seen_in} says {seen_tier or 'read-only clone'}, "
                    f"{check_id} says {tier or 'read-only clone'}"
                )
    assert disagreements == [], (
        "the same tool is classified two ways: " + "; ".join(disagreements)
    )


def test_the_classification_is_not_vacuous():
    """`test_a_tool_has_one_tier_across_the_family` passes trivially on a
    tree where nothing is classified, which is the state this change exists
    to leave behind. Assert the sweep actually happened, so deleting every
    `needs:` key fails loudly instead of turning the guard above into a
    no-op. If this fails, a classification was removed - restore it rather
    than lowering the floor.
    """
    checks, errors = ac.load_checks(ac.SKILLS_DIR)
    assert errors == []
    classified = sorted(c.id for c in checks.values() if c.needs)
    assert len(classified) >= 15, (
        f"only {len(classified)} record(s) classify any tool: {classified}"
    )
    assert {t for c in checks.values() for t in c.needs} == set(ac.NEEDS_TIERS), (
        "both tiers should be in use across the family"
    )


def test_a_record_that_classifies_a_tool_states_a_fallback():
    """A `needs:` entry is machine-readable and says nothing about what to
    do instead. `## Tooling fallback` is where an executing agent reads
    that, so a record admitting one of its tools needs a grant must have
    the section - otherwise the agent reaches for the tool, it fails, and
    the check reports `no-evidence` for a reason the record could have
    predicted. If this fails, write the section - do not weaken the
    assertion.

    This deliberately checks that the section exists and not that it names
    each classified tool. `deps/transitive-licenses` defers its whole
    fallback to `deps/licenses` by reference rather than restating the
    tool list, which is the right shape for that record; an
    every-name-must-appear rule would force it to duplicate exactly what
    it was written to avoid. Whether the prose actually explains the
    consequence is a reading pass, not a test.
    """
    checks, errors = ac.load_checks(ac.SKILLS_DIR)
    assert errors == []
    silent = sorted(
        check_id
        for check_id, check in checks.items()
        if check.needs
        and not re.search(
            r"^## Tooling fallback\n\s*\S",
            check.path.read_text(),
            re.M,
        )
    )
    assert silent == [], (
        f"these records classify a tool and state no fallback: {silent}"
    )
```

- [ ] **Step 2: Run them**

Run: `uv run pytest tests/scripts/test_audit_checks.py -q -k "tier_across or vacuous or classified_tool"`

Expected: PASS, because Tasks 2-4 already classified the tree. If `test_a_tool_has_one_tier_across_the_family` fails, a sweep task missed a record naming a shared tool - fix the record, not the test.

- [ ] **Step 3: Probe each test on a throwaway copy**

A test that cannot fail is worse than no test. Verify each one detects what it was written for, on a copy outside the repository so the working tree is never dirtied:

```bash
SCRATCH=$(mktemp -d)
cp -R .agents "$SCRATCH/"
```

Probe A - disagreement. Edit one record in the repo to remove a single tool from its `needs:` list where another record classifies the same tool, run `uv run pytest tests/scripts/test_audit_checks.py -q -k tier_across`, confirm it FAILS naming that tool, then `git checkout -- <that file>`.

Probe B - vacuity. Confirm the floor bites by temporarily raising it: change `>= 15` to `>= 10_000`, run the test, confirm it FAILS reporting the real count, then change it back.

Probe C - unexplained tool. Add a bogus name to one record's `tooling:` and to its `needs:` without mentioning it in `## Tooling fallback`, run `-k classified_tool`, confirm it FAILS, then `git checkout -- <that file>`.

Record the observed count from Probe B in the commit message, so the floor's headroom is on the record.

- [ ] **Step 4: Run the full gate**

```bash
uv run pytest tests/ -q
uv run ruff check . && uv run ruff format --check .
uv run python scripts/render_handbook_traceability.py --check
git status --short
```

`git status --short` must show only `tests/scripts/test_audit_checks.py` - the probes above must all have been reverted.

- [ ] **Step 5: Commit**

```bash
git add tests/scripts/test_audit_checks.py
git commit -m "test: hold the tool classification to one tier across the family

An absent needs: entry is a positive claim that the tool runs against a
read-only clone, so no test can tell a record nobody classified from one
deliberately left at the default. Where a tool appears in more than one
record, though, a missed record shows up as two records disagreeing about
the same tool, and that is checkable.

The vacuity floor is the other half: the disagreement test passes trivially
on a tree where nothing is classified, which is the state this change
exists to leave behind.

Refs #19"
```

---

### Task 6: The engine states the axis, the grants and the reasons

Spec decisions 1, 2, 3, 4, 5 and 6. This is a prompt change and gets its own commit, per `CLAUDE.md`.

**Files:**
- Modify: `.agents/skills/audit-core/SKILL.md`

**Interfaces:**
- Consumes: the tier names from Task 1 (`resolved-tree`, `target-execution`).
- Produces: the obligation wording Task 8 quotes verbatim in the ledger. Task 8 anchors on the exact phrases written here, so do not reword them afterwards without re-running that task's tests.

- [ ] **Step 1: Add the grants to step 0**

In the bulleted list under step 0 that resolves `target_root`, `target_ref` and `out_path`, add a fourth bullet after `out_path`:

```
- `grants`: whether this run may materialize the target's dependency tree, and whether it may execute the target's own code. Both are **off unless the user grants them**, they are separate, and holding the first does not confer the second. Resolve them here for the same reason the opt-in sub-audits are resolved here: a dispatched agent has nobody to ask, so a permission that has to be asked for is a permission it cannot obtain. Record which were granted, and record the scratch directory each reconstruction used.
```

- [ ] **Step 2: State the axis in step 1**

Append this paragraph to step 1, after the paragraph beginning "A partition's language is a set and never a single value":

```
**What a tool needs *present* is a different question from where it comes from, and a record answers both.** A `tooling:` name may be obtainable and still unable to answer: `knip` is a registry package any one-shot runner can fetch and it wants `typescript` and `@types/node` installed before it reports anything true, while `osv-scanner` is a standalone binary no runner can fetch and it reads a lockfile straight off a read-only clone. The record's `needs:` frontmatter carries the second axis per tool - absent means the tool answers from source, manifests and lockfiles; `resolved-tree` means it needs the dependency graph materialized to read package metadata; `target-execution` means it needs that and runs the target's own code. Read it before choosing a tool, because the failure it prevents is not a tool that refuses to start: it is a tool that starts, finds an empty dependency graph, and reports nothing wrong.
```

- [ ] **Step 3: State the reconstruction policy in step 1**

Append immediately after the paragraph from step 2:

```
**Never install into the target; reconstruct outside it.** Installing dependencies writes to the tree under audit, so it is barred by the invariant below whatever the user granted - and `git worktree add` is barred with it, because it writes `.git/worktrees/` and leaves no working-tree delta, so it would slip past the very `git status --porcelain` comparison that watches for this. Where the run holds the `resolved-tree` grant, copy the target to a scratch directory that does **not** resolve under `target_root` - the same refusal `out_path` gets, for the same reason - and resolve there, with `--ignore-scripts` or that package manager's equivalent. Say so in the report: a reconstructed graph is weaker evidence than a lockfile read in place, because it can differ from what the audited team actually has installed, and a reader who is not told cannot discount it. Where the run holds no grant, the checks whose only tools need one are `no-evidence`, never clean.
```

- [ ] **Step 4: State where install scripts belong**

Append immediately after the paragraph from step 3:

```
**An install hook is execution, not resolution.** A `postinstall` runs third-party code from the target's graph in the audit environment, which is the `target-execution` tier by what it does rather than by when it happens. So a tree that will not resolve with scripts disabled does not license dropping the flag under a `resolved-tree` grant: either the run also holds `target-execution`, or the check is `no-evidence`. This costs real coverage on a graph with native builds, and the alternative costs more - a grant the user understood as "read the licences" silently running whatever a dependency's install hook contains.
```

- [ ] **Step 5: Add the `no-evidence` reasons to step 2**

In step 2, find the sentence that ends "and **`not-applicable`** means the check has no lens in this partition's languages." Immediately after it, insert:

```
`no-evidence` carries a reason, because the three ways a check can fail to run are not equally anyone's fault: `not-permitted` (it needed a grant this run does not hold, so re-running with the grant answers it), `tool-unavailable` (no candidate could be obtained - unfetchable, not installed, or no network, so the audit environment answers it), and `tool-failed` (a tool ran and errored or returned nothing parseable, so neither does). Render it with the status, as `no-evidence (not-permitted)`. The scale itself does not grow: a fourth status would collapse the distinction this paragraph just drew, in the other direction.
```

- [ ] **Step 6: Add `needs` to the record schema paragraph**

In the "Authoring a new auditing skill" section, the sentence listing the frontmatter attributes reads "with its machine-checkable attributes in YAML frontmatter (`id`, `domain`, `locality`, `handbook`, `tooling`, `optin`)". Change that parenthetical to:

```
(`id`, `domain`, `locality`, `handbook`, `tooling`, `needs`, `optin`)
```

Then, in the same section, append to the sentence that begins "Every `## Tooling fallback` **detects before it prescribes**":

```
and a tool that needs more than a read-only clone is named in `needs:` as well as in the prose, so the constraint is machine-readable where a run selects tools and explained where an agent reads what to do instead.
```

- [ ] **Step 7: Extend the no-writes cross-cutting rule**

In the "Cross-cutting rules" section, the **No writes to the target's working tree or git history** bullet ends "because a package manager asked only to read will write a cache or a lockfile into the tree given the chance." Append:

```
Installing the target's dependencies is the same violation done deliberately, so it is never the way to satisfy a tool that needs them; `git worktree add` is barred for the same reason and is the more dangerous case, since it writes only under `.git/` and so leaves the working-tree comparison above green.
```

- [ ] **Step 8: Check the writing rules**

```bash
git diff --stat .agents/skills/audit-core/SKILL.md
git diff .agents/skills/audit-core/SKILL.md
```

`.agents/` is not on the no-em-dash list, but match the file's existing style, which uses ` - ` throughout. Read the diff and confirm no line you did not intend to change was reflowed: every edit above is an insertion or an append to one existing line, so a removed line that you did not append to is a reflow.

- [ ] **Step 9: Commit**

```bash
git add .agents/skills/audit-core/SKILL.md
git commit -m "docs: tell the engine what a tool needs present, not just where it comes from

The engine classified a tooling name by where it is obtained and had no way
to say what must exist in the target before it answers, so an agent learned
the difference by running a tool against an empty dependency graph and
reading the empty result as a clean one.

Adds the tier axis, two default-off grants resolved at scope time because a
dispatched agent has nobody to ask, reconstruction outside target_root
rather than an install into it, and a reason on no-evidence so 'we were not
allowed to look' is distinguishable from 'the tool would not install'.

git worktree add is called out explicitly: it writes only under .git/, so it
is the one way to breach the invariant that leaves the working-tree check
green.

Refs #19"
```

---
### Task 7: The sweep resolves the grants and builds the tree once

Spec decisions 3 and 4 applied to the fan-out, plus the reporting from decision 6. A prompt change, so its own commit.

**Files:**
- Modify: `.agents/skills/audit/SKILL.md`

**Interfaces:**
- Consumes: the obligations Task 6 wrote into `audit-core`.
- Produces: the sweep-side wording Task 8's ledger rows describe.

- [ ] **Step 1: Resolve the grants at step 0**

In `### 0. Scope + mode`, insert a new bullet immediately after the **Inferred rubrics** bullet (it is the third of the same family of reasoning, so it belongs with them):

```
- **Grants for tooling that needs more than a read-only clone - resolve them here too, once, for the whole sweep.** `audit-core` classifies each `tooling:` name by what must be present before it answers: absent means source, manifests and lockfiles suffice, `resolved-tree` means the dependency graph must be materialized, `target-execution` means the tool also runs the target's own code. Both of the latter are permissions, both are off by default, and they are separate - a user who agreed to a licence scan has not thereby agreed to run a stranger's test suite in this environment. This is the same class of question as the two bullets above and gets the same treatment: ask once, before anything fans out, because a dispatched agent has nobody to ask and will otherwise either skip a check the user would have allowed or reach for an install nobody sanctioned. Pass every domain the grants that were resolved, whether or not that domain has a check needing one. Where a grant is withheld, the checks whose only tools need it are `no-evidence (not-permitted)`, which is a different report from `no-evidence (tool-unavailable)` and must not be merged into it.
```

- [ ] **Step 2: Build the reconstructed tree once, in step 1**

The sweep already builds the project inventory once so eight agents do not each rebuild it. A reconstructed dependency tree is the same kind of artifact and a far more expensive one. Append to `### 1. Fan out`, immediately after the paragraph beginning "**Classify each partition's languages by a file census":

```
**If the `resolved-tree` grant was given, materialize the tree once here too, and pass its path.** It is `audit-core` step 1's shared-artifact rule applied to the most expensive artifact in the family: eight domain agents each copying the target and resolving its graph would spend eight installs to produce eight trees that are supposed to be identical, and would be free to disagree about the one thing the grant was obtained to establish. Copy the target to a scratch directory that does not resolve under `target_root`, resolve there with `--ignore-scripts`, and hand every domain the path plus the resolver command and whether the lockfile was frozen. An install hook is `target-execution` however it is triggered, so a tree that will not resolve with scripts disabled needs that grant as well or stays unresolved - do not quietly drop the flag to make an install succeed. The target itself is never installed into, and `git worktree add` is not a shortcut around that: it writes `.git/worktrees/` and leaves the working tree clean, so it passes the check in the cross-cutting rules below while breaching the invariant that check exists to enforce.
```

- [ ] **Step 3: Carry the grants in the dispatch payload**

In the bulleted dispatch list, insert a new bullet immediately after the granted-opt-ins bullet:

```
- **The grants, named explicitly, including the ones withheld** - and where `resolved-tree` was granted, the path to the tree built above, the resolver command and whether the lockfile was frozen. An unstated grant reads to an agent as a question it may answer itself, which is how a report-only sweep acquires an install nobody sanctioned. A withheld grant said out loud is what turns "the tool did not run" into `no-evidence (not-permitted)` rather than a guess about the environment.
```

- [ ] **Step 4: Point the detection-tooling bullet at the second axis**

The long detection-tooling bullet already tells an agent to read a `tooling:` entry before choosing how to *run* it, distinguishing three kinds of thing. Insert this sentence immediately after the sentence ending "so the distinction is what keeps that status honest.":

```
**A second axis runs across all three kinds and the record answers it separately in `needs:`**: what must be present in the target before the tool can answer. It is orthogonal to the kind - `knip` is a registry package a runner fetches happily and cannot report anything true without the tree, while `osv-scanner` is a standalone binary no runner can fetch and answers from a lockfile alone - so obtaining a tool is no evidence that it can run here. Prefer a tool that needs nothing present; reach for one marked `resolved-tree` or `target-execution` only against the tree built at the top of this step and only under the matching grant; and where the grant is absent, report `no-evidence (not-permitted)` rather than running the tool against an unresolved graph, which returns an empty result that reads exactly like a clean one.
```

- [ ] **Step 5: Render the grants and the reasons in the report template**

In the `## How the audit ran` block of the template, insert a line immediately after the `Opt-ins:` line:

```
- Grants: <resolved-tree granted/withheld, target-execution granted/withheld> · Dependency tree: <read in place | reconstructed at <scratch path> with `<resolver command>`, lockfile frozen yes/no | not materialized>
```

And in the coverage paragraph that follows the roll-up table (the one beginning "Coverage is not optional decoration"), append:

```
For the same reason, a `no-evidence` cell carries its reason - `not-permitted`, `tool-unavailable` or `tool-failed` - because a reader deciding whether to re-run the sweep with a grant needs to tell the checks that were refused from the ones nothing could have answered.
```

- [ ] **Step 6: Extend the sweep's own no-writes rule**

In `## Cross-cutting rules`, the bullet **Report-only means no writes to the target's working tree or git history** ends "`git status --porcelain` at the target before and after." Append:

```
Materializing dependencies under a grant does not weaken this: the resolution happens in a scratch copy outside `target_root`, so the comparison at the target must come back identical either way, and a delta is a defect of the audit run whether or not a grant was held.
```

- [ ] **Step 7: Verify no line was reflowed**

```bash
git diff .agents/skills/audit/SKILL.md | grep -c '^-' 
git diff --stat .agents/skills/audit/SKILL.md
```

Every step above is an insertion or an append to an existing line. Removed lines should be only those you appended to. Read the diff and confirm.

- [ ] **Step 8: Commit**

```bash
git add .agents/skills/audit/SKILL.md
git commit -m "docs: make the sweep resolve tooling grants before it fans out

A sweep dispatches parallel agents that cannot ask anything, so a
permission needing a question is a permission no agent can obtain. Left
unstated, an agent either skips a check the user would have allowed or
reaches for an install nobody sanctioned - and a report-only sweep
acquiring an install is the failure this family is built to prevent.

Resolves both grants once at step 0 beside the opt-ins and the rubric
question, which are the same class of decision; materializes the tree once
rather than per domain, since it is the most expensive shared artifact in
the family and eight agents rebuilding it may disagree about the one thing
the grant was obtained to settle; and renders the grant and the no-evidence
reason in the report so a withheld permission is distinguishable from a
missing tool.

Refs #19"
```

---

### Task 8: The ledger, and the record schema in CLAUDE.md

Task 6 added obligations to `audit-core`. The sweep-obligations ledger exists precisely because an obligation the sweep fails to restate leaves no trace in the file that dropped it, so skipping this makes the ledger stale in the way it was built to prevent.

**Files:**
- Modify: `docs/audit/sweep-obligations.md`
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: the exact wording committed in Tasks 6 and 7.
- Produces: nothing later tasks read.

- [ ] **Step 1: Re-read both skills whole**

The ledger's own "How to re-run this check" section says to read `.agents/skills/audit-core/SKILL.md` whole - not a diff - and find a row for every sentence that tells a run to do something. Do that now for the paragraphs Task 7 added, and read `.agents/skills/audit/SKILL.md` whole to see where each is discharged.

- [ ] **Step 2: Add one row per new obligation**

Append these rows to the obligations table in `docs/audit/sweep-obligations.md`. Each anchor must occur **exactly once** in `audit-core/SKILL.md` - the test asserts that, and short anchors that recur in a later recap are the failure mode it was written for. Verify each anchor with `grep -c` before committing.

```
| Resolve the tooling grants at scope time | `whether this run may materialize the target's dependency tree` | restated | Step 0 resolves both, once, for the whole sweep, beside the opt-in list and the inferred-rubric question - the same class of user-decidable question, given the same treatment because a dispatched agent has nobody to ask. |
| The two grants are separate | `holding the first does not confer the second` | restated | Step 0 states it in its own words: a user who agreed to a licence scan has not agreed to run a stranger's test suite in this environment. |
| Read what a tool needs present, not only where it comes from | `is a different question from where it comes from` | restated | Added to the detection-tooling bullet as a second axis running across all three kinds of `tooling:` entry, with the consequence spelled out: an unresolved graph returns an empty result that reads exactly like a clean one. |
| Never install into the target; reconstruct outside it | `Never install into the target; reconstruct outside it` | restated | Step 1 materializes the tree once in a scratch directory outside `target_root`, and the cross-cutting no-writes rule states that the comparison at the target comes back identical whether or not a grant was held. |
| `git worktree add` is barred | `and leaves no working-tree delta, so it would slip past` | restated | Twice, because it is the one breach that leaves the working-tree check green: once where the tree is built, once in the cross-cutting rule that owns the check it would slip past. |
| An install hook is execution, not resolution | `An install hook is execution, not resolution.` | restated | Step 1 forbids dropping `--ignore-scripts` to make a resolution succeed; a tree that will not resolve without hooks needs the execution grant or stays unresolved. |
| Build the expensive shared artifact once | `rather than each rebuilding a possibly-inconsistent copy` | restated | Already a row for the inventory; the reconstructed tree is the same rule applied to the costliest artifact, and the sweep says so where it builds it. |
| `no-evidence` carries a reason | `carries a reason, because the three ways a check can fail to run` | restated | The fan-out brief names the reason vocabulary, the report template renders it in the coverage cell, and step 0 states that a withheld grant produces `not-permitted` rather than being merged into `tool-unavailable`. |
```

The "Build the expensive shared artifact once" row shares its anchor with an existing row. **That will fail the exactly-once anchor test.** Do not add that row: instead extend the existing `Build a shared ground-truth artifact once` row's "how" column to mention the reconstructed tree, leaving one row per anchor.

- [ ] **Step 3: Run the ledger tests**

```bash
uv run pytest tests/test_sweep_obligations.py -q
```

Expected: PASS. If an anchor is reported as occurring zero or more than once, fix the anchor - pick a longer phrase from the sentence you meant to pin - rather than trimming it to whatever fragment survives.

- [ ] **Step 4: Update the counts in the ledger's own prose if it states any**

Read the ledger's intro and Dispositions sections. If any sentence states a row count or a per-disposition count, recompute it and correct it; if none does, change nothing. Never assert a count you did not compute.

- [ ] **Step 5: Add `needs:` to CLAUDE.md**

In the `## Check records` section, the opening sentence lists the frontmatter fields: "`id` (`<domain>/<slug>`), `domain`, `locality` (`local` or `global`), `handbook` (list of matrix row ids, may be empty), `handbook_note` (required when `handbook` is empty), `tooling` (optional), `optin` (default false)". Insert `needs` after `tooling`:

```
`tooling` (optional), `needs` (optional; maps `resolved-tree` or `target-execution` to tool names drawn from `tooling`), `optin` (default false)
```

Then append a paragraph to that section:

```
`needs` is the second axis on a tooling name. `tooling` says where a tool comes from; `needs` says what must be present in the target before it answers - nothing beyond a read-only clone by default, a materialized dependency graph for `resolved-tree`, that plus running the target's own code for `target-execution`. The names repeat those in `tooling` on purpose and the validator checks the repetition, so a rename that misses one of the two places fails the gate. An omitted tier is a positive claim that no tool here needs it, which is why a record left unclassified reads as clean rather than as unfinished; the only mechanical guard is that a tool named by two records must be classified the same way in both.
```

- [ ] **Step 6: Run the full gate**

```bash
uv run pytest tests/ -q
uv run ruff check . && uv run ruff format --check .
uv run python scripts/render_handbook_traceability.py --check
```

- [ ] **Step 7: Commit**

```bash
git add docs/audit/sweep-obligations.md CLAUDE.md
git commit -m "docs: account for the obligations this change added to the engine

The ledger's premise is that an obligation the sweep fails to restate
leaves no trace in the file that dropped it, so an engine change that skips
the ledger makes it stale in exactly the way it exists to prevent. This is
the first change since it shipped to add obligations to audit-core.

Refs #19"
```

---

## Self-review

Run this checklist against the spec before handing the plan over.

1. **Spec coverage.** Decision 1 (the tier axis) is Task 1 for the vocabulary and Tasks 2-4 for the classification; decision 2 (never install, `git worktree add` barred) is Task 6 steps 3 and 7 plus Task 7 steps 2 and 6; decision 3 (two grants) is Task 6 step 1 and Task 7 steps 1 and 3; decision 4 (reconstruct outside and say so) is Task 6 step 3 and Task 7 steps 2 and 5; decision 5 (install scripts are execution) is Task 6 step 4 and Task 7 step 2; decision 6 (`no-evidence` reasons) is Task 6 step 5 and Task 7 step 5; decision 7 (the schema) is Task 1, with the guards in Task 5 and the ledger in Task 8.
2. **Acceptance criteria.** All four map onto the tasks above via the spec's own mapping table. The third - "check records note which of their tools need a resolved tree" - is met by Tasks 2-4 over every record carrying `tooling:`, and the plan's tier table records the verdict for the tools that stay at the default so the reasoning is not lost.
3. **No placeholders.** Every code block and every prose insertion is written out in full. The record edits in Tasks 2-4 name the exact frontmatter and state the facts to write rather than the sentences, because the records are written in their own voices and a pasted sentence would read as an intrusion; the facts themselves are given in full and verified.
4. **Type consistency.** `NEEDS_TIERS`, `Check.needs`, `resolved-tree` and `target-execution` are spelled the same in Task 1, in every record table, in the tests in Task 5 and in the prose in Tasks 6-8.

## What this plan does not verify

There is no foreign target in this repository, so no task exercises a reconstructed-tree audit end to end. Tasks 6 and 7 write prose an agent will read at run time, and nothing here proves an agent follows it. The mechanical half is covered: the loader rules have unit tests, the cross-record classification has a consistency test with a vacuity floor, the ledger anchors and quotations are tested, and the integrity gate runs. Say this in the PR rather than implying a fixture run happened.
