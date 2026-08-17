# Harness transcription drift: design

Closes the gap in issue #51. `scripts/run_python_fixture_lens.py` opens by promising that its `INVOCATIONS` table holds each check record's prescribed invocation verbatim. That promise is what makes the harness an instrument rather than a second opinion: where it deviates to make a tool run, the deviation is the finding, and it is visible as a diff against the transcribed command. Two entries now break the promise, and no guard failed.

## The defect, per entry

The two entries drifted for two different reasons, which is why one fix does not cover both.

**`arch/cycles`** - the anchor guard was watching and stayed green. Its `record_quote` is the paragraph's first sentence, naming `pydeps --show-cycles`. The new prescription landed in a later sentence of the same paragraph: "Append `--show-dot` to that `pydeps` invocation". The transcribed `('pydeps', '--show-cycles')` still traces through the old quote as a token subsequence, the quote still occurs exactly once, and it still ends at a sentence boundary. Three guards, all green, prescription changed.

**`deps/vulnerabilities`** - the anchor guard was never watching. The entry sits in the `unanchored` exception set because the record writes a `<requirements>` placeholder rather than a resolvable path. That exception, added to accommodate a placeholder, switched off the only guard that would have noticed a flag pair being added to the prescribed form.

So the exception set is itself a hole, and every existing guard runs harness to record. Nothing runs record to harness, which is the direction both defects live in.

## The guard: dispositioned command forms

For each `(check, tool)` the harness declares every command form its record's prescribing paragraph names, each carrying one disposition. A test extracts the forms mechanically and asserts the extracted set equals the declared set.

### Extraction

The boundary is **the paragraph containing `record_quote`**, not the `**Python**` review-lens line. Of the 26 records carrying a `python:` tooling entry, 23 have exactly one `**Python** - ` paragraph and 3 have none: `arch/complexity-gate` prescribes in an unlabelled bolded directive, `docs/docstring-coverage` likewise, and `deps/transitive-licenses` delegates its whole prescription to `deps/licenses`. Anchoring on `record_quote` covers all 26 and reuses a field three guards already hold. Markdown here is never hard-wrapped, so that paragraph is exactly one source line.

Within that line, from its backtick spans:

- A **command form** is a span whose first token is the tool's name and which has at least two tokens.
- A **flag span** is a span whose first token begins with `-`.
- A span that is only the bare tool name is a **mention**, not a form. This is what lets `deps/vulnerabilities` name a bare `pip-audit` in order to forbid it ("Run `pip-audit` with no arguments and it audits whatever environment it was launched from ... so don't") without needing an entry.
- Every other span is ignored: a filename glob, a stderr line, a dot edge, or another tool's command cited for context.

Measured against the two records as they stand, extraction yields for `pydeps` one form (`pydeps --show-cycles`) and two flag spans (`--show-cycles`, `--show-dot`); and for `pip-audit` three forms (`pip-audit --locked .`, `pip-audit -r <requirements>`, `pip-audit -r <requirements> --no-deps --disable-pip`) and three flag spans (`--disable-pip`, `--locked`, `--no-deps`).

### Dispositions

A starting vocabulary, deliberately not final:

| Disposition | Meaning |
|---|---|
| `runs` | the harness executes this form |
| `alternative` | a form for a partition shape this fixture set does not have |
| `superseded` | a form the record names and then narrows |
| `forbidden` | a form the record names in order to warn against |

Which values survive is decided by the re-transcription pass below, not by this spec. Property 3 below deletes any value nothing uses, so the vocabulary cannot accumulate ceremony that reads as coverage. This mirrors how `needs` was introduced: a classification sweep over the records, then a guard that fails when the classification goes vacuous.

### The four properties

Each catches something the others cannot.

1. **Extracted set equals declared set**, per `(check, tool)`. A record that grows a command form the harness has not declared fails, naming the span.
2. **Every flag span occurs inside at least one declared form** for that paragraph. A flag the record names that no declared form contains is a new prescription. This is the property that catches `arch/cycles`: `--show-dot` occurs in no declared form today.
3. **Every `runs` form appears in some partition's argv**, and every disposition value in the vocabulary is used by at least one entry. The first half is the missing record-to-harness direction and is what catches `deps/vulnerabilities`: declaring `pip-audit -r <requirements> --no-deps --disable-pip` as `runs` fails while the pip partition's argv carries only `('pip-audit', '-r', 'requirements.txt')`. The second half keeps the vocabulary honest.
4. **Within `## Tooling fallback`, spans naming the tool occur only in the quoted paragraph.** Without this, a future correction that appends a whole new paragraph escapes a guard scoped to one paragraph, which is the same blind spot one level up.

Properties 2 and 3 catching one entry each is the design's own evidence that both directions were needed.

## Rewording `arch/cycles`

`--show-dot` becomes part of a whole prescribed command rather than an instruction to append one. Proposed form for the bolded sentence:

> **Run `pydeps --show-cycles --show-dot`: `--show-cycles` alone has no textual output channel at all.**

The reason is structural rather than cosmetic. A record that prescribes by appending a flag to a previously named command cannot be anchored by any single-sentence quote, because no one sentence carries the whole command in argv order. That phrasing is what invited the drift, and it is the only instance of it: across every `**Python** - ` paragraph in the family, `Append \`--show-dot\`` is the sole append-shaped prescription. `deps/freshness` already writes its corrected command whole, as `uv pip list --outdated --python <path-to-venv-python>`, so this makes `arch/cycles` consistent with its sibling rather than introducing a style.

After the reword, extraction yields two forms for `pydeps` (`pydeps --show-cycles`, superseded, and `pydeps --show-cycles --show-dot`, runs) and one flag span (`--show-cycles`), which occurs in both. The re-transcribed argv anchors in the new sentence, and argv plus its `src/fixture_app` completion still does not, so the completion guard holds.

This is a prompt change and lands in its own commit, stating why.

## Re-transcription pass

Issue #51's first criterion requires re-verifying `INVOCATIONS` by reading the records rather than the previous transcription. That is all 26 records and all 50 invocations. The two known entries are what one reviewer found; the pass may find more, and finding more is the expected outcome rather than a surprise. Reading the records against the existing table is how the drift survived in the first place, so the pass reads the records first and compares second.

## Re-running, scoped per entry

`arch/cycles` is re-run with the corrected command and its result published. `deps/vulnerabilities` records provenance instead: `pip-audit -r` is non-functional on the host that ran this round, where `ensurepip` aborts with SIGABRT, so a re-run produces another host-defect `no-evidence` and buys nothing. Uniformity here would be a worse record than honesty per entry.

Two consequences follow and belong in the plan rather than in a reviewer's findings.

**`arch/cycles` needs a second prose edit.** It currently states that the `--show-dot` behaviour was measured in a scratch copy "not as an artifact of the python lens smoke run, whose own results show only the bare `--show-cycles` form". Publishing the re-run makes both halves of that sentence false.

**Re-run observations carry their own date.** `uvx` resolves the latest release at run time, so a re-run can observe different tool versions than the rows published for 2026-08-14. Folding them silently into that date would make the record claim a measurement it did not take.

## Two smaller items

`inner_uv_target`'s docstring still describes `--python` as "harness plumbing rather than a claim from any record", which `deps/freshness` has since made a record claim.

`test_folding_a_completion_into_the_argv_breaks_the_anchor` pins the number of invocations carrying a completion. `arch/cycles` keeps its completion through the re-transcription, so that number is expected to hold, and the plan recomputes it rather than trusting this sentence.

## Out of scope

No new audit domains, no changes to the grader, no re-run of unaffected rows, and no extension of the guard to the TypeScript side, which has no harness to drift.

## Acceptance criteria

- [ ] `INVOCATIONS` matches every record's prescribed invocation, re-verified by reading all 26 records rather than the previous transcription, with anything found beyond the two known entries listed.
- [ ] The four properties above are implemented as tests, and each is shown to fail when the drift it targets is reintroduced.
- [ ] `arch/cycles` prescribes `pydeps --show-cycles --show-dot` as one command, in its own prompt commit stating why.
- [ ] `inner_uv_target`'s docstring matches what `deps/freshness` now claims.
- [ ] `arch/cycles` is re-run and its result published with its own date and tool versions; `deps/vulnerabilities` states that its published observation predates the re-transcription.
- [ ] The `arch/cycles` record no longer claims the `--show-dot` behaviour is absent from the lens run's own results.

## Related

- #51 - the issue this closes
- #45 - the round whose record corrections introduced the drift
- #46 - the JS/TS fixture round, which will correct records the same way and is the reason this guard goes in first
