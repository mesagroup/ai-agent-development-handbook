# A glued placeholder needs a delimiter, and a prescription needs a backtick span

Issue #56. The form extractor #53 built reads a record's prescribed commands out of the inline backtick spans on one paragraph. Three shapes of prescription escape that reader, and one of them escapes in the direction that reads as clean.

**Status.** Written and self-approved under autonomous mode, with no maintainer review gate, as the second nightshift loop's first item (ledger #86). Every decision below names the alternative it rejected, so any one of them can be reopened on evidence rather than on recollection. The gate that was not granted is the review of the resulting PR.

## The degeneration, reproduced before designing anything

`_concrete` truncates a token carrying a glued placeholder at the `<` and leaves the `<` on as the mark `_matches` reads as "prefix, plus something after it". Observed on `origin/main` at `bb784a0`:

| call | result | should be |
|---|---|---|
| `_matches("--cov=<", "--cov=pkg")` | `True` | `True` |
| `_matches("--cov=<", "--cov=")` | `False` | `False` |
| `_matches("-r<", "-rf")` | **`True`** | `False` |
| `_matches("-<", "-x")` | **`True`** | `False` |
| `_matches("-<", "--verbose")` | **`True`** | `False` |

The last three are the hole. `-<` is satisfied by any flag at all, which is a marked token that asserts nothing while looking like an assertion, and this is the only one of #56's three shapes that fails in the false-clean direction: a drifted command passes.

Neither shape is live. **No record in the tree writes a glued placeholder whose head is a bare short flag.** Computed over all 77 records, the heads that reach `_concrete` today are `--cov=`, `--randomly-seed=`, `--sequence.seed=`, `--package=@stryker-mutator/`, `@stryker-mutator/`, `file://` and `https://pypi.org/pypi/`. Every one ends in `=` or `/`. The `"` that `arch/complexity` writes in `"<path>:<line> <function>"` never reaches `_concrete`, because `_tokens` strips a leading quote first and the head is then empty, which drops the token rather than marking it.

## The mark is trustworthy exactly where its head ends at a value delimiter

`_marked` gains that condition: a token ending in `<` is a mark only where the character before the `<` is `=`, `:` or `/`. Anything else - an alphanumeric, a `-`, or nothing at all - is not a mark, so `_matches` falls back to exact equality and a short flag can no longer be satisfied by an unrelated flag sharing its prefix.

**Rejected: a minimum unmarked prefix length**, which is #56's first suggestion and the ledger's first granted option. Length is a proxy for unambiguity and it is the wrong proxy: `-ab<` is three characters and is satisfied by `-abc` exactly as `-r<` is satisfied by `-rf`. What makes `--cov=<` safe is the `=`, not the six characters before it, because no other option can be spelled `--cov=` and mean something else, while `-r` is a genuine prefix of a different flag. This is that suggestion made structural rather than a different answer to a different question, and it is recorded here, on #56 and on #86 rather than only in this file, because a decision the tracker cannot see is a decision nobody can check.

**Rejected: comparing the marked token against the whole span**, #56's second suggestion. Reconstructing `-r<file>` and asking whether `-rf` fits it answers yes for the same reason the prefix test does, so it moves the comparison without closing the hole.

`_marked` stays the one place that decides what a mark is, which is what its docstring already argues for; the delimiter is now part of that definition rather than a second condition kept in step with it somewhere else.

## The matcher alone would fail obscurely, so a record-level guard says why

With the rule above, a record that someday writes `pip-audit -r<requirements>` produces the token `-r<`, which is no longer a mark and which no real command token equals, so the coverage property fails with "this token is missing" about a token the record did write. That is a true failure with a misleading cause.

So a guard over every record refuses that shape by name: a glued placeholder whose head does not end in a value delimiter is unverifiable, and the record writes the value space-separated instead. The guard is what makes the limit legible; the matcher is what makes it safe. Neither substitutes for the other, and the guard's floor is the tree's own count of zero such tokens, so it fails the moment one appears rather than counting up to a number someone has to maintain.

## A prescription in a fenced block is answered by enforcing the convention

`scripts/audit_checks.py` rejects a check record whose body carries a fenced code block, in ``` or `~~~` form. **No record carries one today**, computed over all 77, so this states a convention the tree already keeps rather than asking for a migration.

**Rejected: teaching the extractor to read fences.** Reading them is mechanical, and that is the objection rather than the argument for it: it puts a second reader over the same records, and every reader added over one source is a second authority that nothing holds against the first. The record schema exists to avoid exactly that shape.

The rejection's blast radius is deliberate and worth stating rather than discovering. A loader error excludes the record from `load_checks`' mapping, so a fenced block in one record removes that check from every audit run. That is the same severity the `## Tooling fallback`-beside-`routes:` rejection already carries, and it is the right one: an integrity gate makes it a red suite before it can ship, and the alternative - loading a record whose prescription no guard can read - is the absent-check-reads-as-clean failure this family exists to prevent.

**An indented block stays legal.** `arch/complexity` uses one to show a tool's observed output, which is not a prescription and which nothing needs to extract. The convention is about where a *prescribed command* lives, and the error message says so, so that nobody reads the fence rule as a ban on showing output.

## The unbackticked case is an accepted limit, and it needs the convention beside it

"Also pass `--max-bacon 2`" written without backticks is invisible to the extractor, and reading unbackticked prose is not mechanical. It is also probably the wrong goal: the answer is the convention above, that every prescribed command appears in an inline backtick span, now enforced for the one shape that could hide a command in plain sight.

That limit is recorded where a reader of the extractor meets it - in the module's own docstring - and the convention it rests on is stated in `CLAUDE.md`'s check-record section, which is where a record author reads what a record may contain. A limit recorded only in an issue is a limit the next author will not find.

## What this change does not touch

No module is added under `scripts/`, so `[tool.deptry] known_first_party` is unchanged and `tests/test_deptry_gate.py`'s list still matches the directory. #86 named that rule as a concern for this item because it edits `scripts/`; the edit is to an existing module, so the concern does not arise. `deptry` is run anyway rather than reasoned about.
