# The data-protection audit domain (#4)

*Design spec. The verification counterpart of handbook Part 10, and the ninth domain on the `audit-core` engine.*

## Context

Part 10. Data protection & privacy landed in #47, which existed because this issue could not be built without it: seven of the eight dimensions #4 names had no handbook clause to ground a check record in, so every record would have carried an empty `handbook:` and a `handbook_note` conceding the whole domain sat outside the normative tree it verifies. That is now fixed. Eleven matrix rows carry the `data-protection/` prefix, eight of them with `gap: {recommendation: new-domain, target: "#4"}`, and each of those gap notes says in prose what no existing skill can see. Those notes are the specification this design follows; where this document and a gap note disagree, the note is the one that was reviewed.

## Problem

`security-audit` reads first-party code for secrets and personal data reaching a log or an error message. Nothing in the family reads a data-flow map, a processor register, a pinned region, a retention limit, a deletion path, or a stored trace. So a repository processing personal documents for European data subjects can pass every one of the eight existing lenses while holding no register, pinning no region, and carrying an eval dataset built from real customer files. The audit family's own rule is that absence of a lens is never absence of findings, and the matrix already records this absence honestly. This issue closes it.

## Goals

- A `data-protection-audit` domain skill on `audit-core`, discovered by the `/audit` front door like the other eight.
- Check records covering the eight dimensions #4 names, each grounded in a real Part 10 matrix row rather than in a `handbook_note`.
- The reciprocal half of every edge: each row's `checks:` entry, and each gap either retired or converted to the residue that survives the check.
- A sub-processor inventory available as an opt-in deliverable.
- Cross-links, not duplicates, with `security-audit` (the call-site half of the trail claim), `deps-audit` (the package graph, which no HTTP provider enters), and `eval-audit` (redaction's quality cost as a dimension).

## Non-goals

- Legal judgment. The skill reports what the repository shows and names what it cannot see; whether an agreement suffices is not its question.
- A rewrite of `security/sensitive-data`. The near-miss mapping on the trail row stands, and the new check owns only the residue that record does not reach.
- Deriving the provider surface twice. #6 wants the same surface for pinning and EOL; this issue builds it and that one consumes it.

## Design

### Naming, and why nothing is chosen here

The directory is `.agents/skills/data-protection-audit/`. The loader derives the domain from the directory name with `SKILL_SUFFIX` removed, giving `data-protection`, and validates that every record's `id` is `<domain>/<slug>`. The eleven matrix rows are already prefixed `data-protection/`. So the name is fixed by three things that already agree, and picking anything else would break the loader, the rows, or both.

### Applicability: asked once, and answered honestly when nobody can be asked

A target that processes no personal data would otherwise collect a stack of Criticals - no register, no map, no retention limit - that are noise rather than findings. So the run asks, at scope time, whether the target processes personal data at all.

**Asking it has to be built rather than assumed, and the first draft got this wrong.** Neither engine file contains the words *personal data* anywhere: `audit-core` step 0 resolves subject, depth, mode, `out_path`, grants and opt-ins, and the sweep's own step 0 adds scope and inferred rubrics. A skill file saying the question "is asked there" describes a mechanism that does not exist, which leaves the declaration branch unreachable on the sweep path and reachable on a direct invocation only by accident, because the skill file happens to be in context to prompt it. Two edits make it real, and they follow the shape the sweep already uses for opt-ins, inferred rubrics and grants - all three of which live there *because* a dispatched agent has nobody to ask. The domain's `SKILL.md` **instructs** the run to ask rather than reporting that something else did. And `audit/SKILL.md` gains the declaration in its step 0 and in its fan-out brief, so the sweep resolves it once and passes it; the sweep needs both, because its own text says it "substitutes its own steps for the `audit-core` loop rather than running it, so it inherits none of that step implicitly". `audit-core` itself is deliberately left alone: this declaration scopes one domain rather than every run, so it belongs with the sweep's per-domain scoping questions, and editing the engine would pull in the `sweep-obligations.md` recheck for no gain.

**Asked and answered no.** The domain is out of scope for that run. The report says so and names the operator's declaration as the reason, exactly as the front door already reports a domain the user named that has no checks directory. It does **not** report `not-applicable` on eleven rows: that status means the check has no lens in this partition's languages, and loading a second meaning onto it would make a polyglot gap and an operator's scoping decision indistinguishable in the one column a reader uses to tell measured from unmeasured. Nor does the declaration become a pass. It is an assertion about the target made by someone outside it, which is precisely the class of claim Part 10 requires a report to separate from what the repository shows.

**Nobody to ask.** A sweep's dispatched domain agent and a non-interactive run both have nobody, so the default is that the lens runs and the **absence of a documented personal-data surface is itself the finding**. This is `audit/SKILL.md`'s existing no-inferred-rubric rule, applied to this domain: "you have not written this down" is a diagnosis, and "you violate the standard I invented for you" is not. The rule also decides what the checks may not do, which matters more: no check infers a personal-data surface from field names or file paths and then flags violations against the surface it invented.

### The eight checks

One record each, at `.agents/skills/data-protection-audit/checks/<slug>.md`.

| id | locality | Grounds | What it settles |
|---|---|---|---|
| `data-protection/data-flow-map` | global | `know-what-personal-data-you-hold-and-where-it-goes` | A map exists beside the code, is maintained with it, and is falsifiable against it: reconcile the stores and outbound edges it lists against the ones the code shows. |
| `data-protection/processor-register` | global | `...-register-must-match-the-code-a` | The register exists and carries, per processor, a DPA status, a position on training, and a retention window, with the date of the last reconciliation recorded. Reports the signed-agreement half as not visible from here. |
| `data-protection/provider-surface` | global | `...-register-must-match-the-code-b` | Derive the outbound provider surface from the code - SDK imports, configured base URLs, MCP servers and tool endpoints, the credentials the deployment carries - and reconcile it against the register. A provider reachable from the code and missing from the register is the finding. |
| `data-protection/residency-pinning` | local | `keep-the-data-where-the-law-lets-it-be-a` | The region is pinned explicitly in configuration, required rather than defaulted, and validated at startup with the missing key named in the error. |
| `data-protection/boundary-minimization` | local | `minimize-before-the-boundary` | Redaction, pseudonymization or truncation sits in the one shared outbound call path rather than at each call site, and its quality cost is measured as an eval dimension rather than assumed in either direction. |
| `data-protection/retention-limits` | global | `retention-and-deletion-are-design-decisions-not-cleanup` | Every store holding personal data has a retention limit that something enforces: a TTL, a lifecycle rule, or a scheduled job with a test. |
| `data-protection/deletion-path` | global | `retention-and-deletion-are-design-decisions-not-cleanup` | A deletion path exists, walks the data-flow map through the derived copies (embeddings and the vector index, cached responses, traces, run artifacts, eval datasets and fixtures, backups), and is tested. |
| `data-protection/stored-artifact-pii` | global | `personal-data-does-not-belong-in-the-trail` | Personal data in stored traces, run records, eval datasets and the fixtures extracted from real cases - the residue `security/sensitive-data` does not reach, since it reads call sites rather than artifacts. |

**Why retention and deletion are two records against one row.** A store with no enforced limit and a deletion path that reaches the primary store but not the vector index are different findings, with different fixes, and one can be clean while the other is a Critical. `audit-core` splits a check when a status cannot be shared, not when a handbook section can. Two records citing one row is already the shape on the trail row, which cites `security/sensitive-data` and will cite `stored-artifact-pii`.

**Why `provider-surface` is `global` even though imports are per-partition.** The derivation is per-partition and the *finding* is not: it is "reachable from the code and absent from the register", which needs the union of every partition's outbound edges on one side and a single repository-level register on the other. No per-partition agent can compute either. This is the case `audit-core` describes as decidable per-partition except for one repo-global fact, resolved the way it says - the global check owns it rather than N agents each reporting a partial union.

**Why `residency-pinning` and `boundary-minimization` are `local`.** Configuration and the outbound call path both live in a partition, and a monorepo where one service pins its region and another defaults is exactly the finding, which a global check would flatten into one row. They ride the per-partition agent rather than getting their own.

### Tooling: eight reading records, and one to research first

Seven of the eight are reading records with no `tooling:` key and a `## Tooling fallback` section saying what to read instead. This is not a shortcut. The evidence in this domain is a register, a map, a configuration key, a lifecycle rule and a stored artifact; there is no scanner that enumerates a project's processors, and a record that named one would be prescribing a tool that cannot answer its question. Leaving `tooling:` off also keeps these records clear of the `needs:` tiers, the `ungranted_note` requirement and the TypeScript-lens rule, all of which exist to constrain tools.

`data-protection/stored-artifact-pii` is the one check a scanner could genuinely serve, since it reads data files for personal data. Whether it carries `tooling:` was decided by research, not by preference, against the repository's own bar: a name verified against the tool's own documentation, of a kind a one-shot runner can execute rather than import, and covering TypeScript as well as Python, because a record carrying `tooling:` with no `typescript:` or `any:` key fails `test_every_tooling_record_offers_a_typescript_lens` and would have to join that test's exception set, which is reserved for named debt. The failure being avoided is specific and has happened here: the unscoped `cyclonedx-npm` is a dependency-confusion placeholder rather than the CycloneDX generator, so a runner fetches it, runs it, and produces nothing, which is indistinguishable from a tool that ran and found the artifacts clean.

**The research returned one nameable candidate: `pdscan`**, under `any:`, which is the lens shape `security/secrets-in-code` already uses for a language-agnostic scanner. It is a standalone Go binary in no language registry - the same kind, and the same "no one-shot runner can supply it" caveat, as `osv-scanner` in `deps/vulnerabilities` - it answers from a read-only clone, so it carries no `needs:` tier and therefore must **not** carry an `ungranted_note`, which the validator rejects as vacuous where no tool is tiered. It does personal data rather than credentials, which is the distinction that disqualifies the obvious reuse: `gitleaks`, `trufflehog` and `detect-secrets` all scope themselves to credentials in their own documentation, and a credential is not a data subject, so `security/secrets-in-code`'s tooling list is not transferable here.

Naming it forfeits nothing, because `audit-core` defines `no-evidence` as no tooling **or fallback** being able to run: a `## Tooling fallback` prescribing the reading pass still governs wherever the binary is absent, while a record with no `tooling:` at all would give an audit environment that does have it nothing to run. Two caveats have to travel in the record's prose, because both would otherwise turn a tool that ran into a clean result. Its rules are US-shaped and regex-based - a US social-security number's shape, US street suffixes, a list of common US surnames - with no coverage of passports, IBANs or non-US national identifiers, so empty output discharges the check only on the axes it scans and the rest falls to reading. And its flag that prints the matched values propagates the leak the check exists to find, so a finding reports the location and the rule, not the value.

### The reciprocal matrix half

The matrix row's `checks:` entry and the record's `handbook:` entry are two directions of one edge, so every row below changes in the same commit as the record that cites it. Five gaps retire because the check answers the whole claim. Four convert to a residue, which is a different entry rather than a smaller one: `unchecked` means nothing checks the clause and closing it needs new capability, `residue` means something checks it and part of the claim is still out of reach.

| Row | `checks:` after | Gap after |
|---|---|---|
| `know-what-personal-data-you-hold-and-where-it-goes` | `data-flow-map` | retired |
| `...-register-must-match-the-code-a` | `processor-register` | `report-only` residue: whether the agreement was signed, and whether the provider honours what it published |
| `...-register-must-match-the-code-b` | `provider-surface` | retired |
| `keep-the-data-where-the-law-lets-it-be-a` | `residency-pinning` | `report-only` residue: whether a destination outside the permitted region is actually covered by adequacy, standard contractual clauses or binding corporate rules |
| `keep-the-data-where-the-law-lets-it-be-b` | unchanged | unchanged - already `process`, and a provider's failover behaviour is still not in the target's tree |
| `minimize-before-the-boundary` | `boundary-minimization` | retired |
| `retention-and-deletion-are-design-decisions-not-cleanup` | `retention-limits`, `deletion-path` | `report-only` residue: whether a deletion propagated provider-side and into backups |
| `personal-data-does-not-belong-in-the-trail` | `security/sensitive-data`, `stored-artifact-pii` | `report-only` residue narrows to fixture provenance - synthetic or consented is not a repository fact |
| `verify-against-the-real-artifacts` | unchanged (none) | `new-domain` #4 becomes `report-only` |
| `checklist-a-data-protection-sweep` | unchanged (none) | unchanged (none) |
| `see-also` | unchanged | unchanged |

**The standing-check row is the one to get right, and precedent decides it.** `data-protection/verify-against-the-real-artifacts` is `new-domain` today because its note says `audit-core` "has no lens in this domain to apply them through". This issue supplies the lens, which removes that reason and leaves only the audit cadence itself - whether the sweep is actually run, and whether past reports separated clean from not-visible-from-here. That is outside every skill's evidence base, and the two rows making the same claim, `lifecycle/make-the-standard-executable-and-audit-periodically-b` and `security-supply-chain/verify-against-the-real-artifacts`, both carry `report-only` and cite no check. This row joins them rather than acquiring a check that would have to audit the auditor.

**The checklist row stays unmapped, also by precedent.** All seven checklist rows in the matrix carry no checks and no gap: a recap adds the act of working the list, and each item is owned by a row above it. Mapping the recap would double-count every check it recaps.

### The skill file

`data-protection-audit/SKILL.md` states the lens and defers the loop. `audit-core` says the header holds only what does not vary by check, and warns against copying another domain's word count forward as a target, so its length follows from what this domain has that no single record can hold:

- **Subject:** the personal-data surface - where it enters, every store it rests in, every outbound edge leaving the trust boundary - and the register and map that are supposed to describe it. Established first, because it is what every check is a question about, the way `security-audit` establishes trust boundaries first.
- **The applicability rule** above, which is cross-cutting and belongs to no record.
- **Slicing:** the two `local` records ride the per-partition agent; each `global` record gets its own agent over the whole subject. `provider-surface` and `data-flow-map` both consume the same derived outbound surface, so it is built once as a shared artifact rather than twice.
- **Status scale:** `ok / warn / violation`, and the domain's own restatement of the rule that matters most here - a claim the repository cannot see is reported as unverifiable-from-here with what would settle it and who holds that evidence, never as `ok`. Part 10 names this the easiest rule in the part to break. **It rides the scale as a mandatory annotation, not as a fourth value**: `warn (unverifiable-from-here)`, rendered the way `audit-core` renders `no-evidence (not-permitted)`. `audit-core` states outright that the scale does not grow, every one of the eight sibling domains only ever *renames* the same three values in its own vocabulary, and the sweep's coverage triple counts checks that ran, `no-evidence` and `not-applicable` - so a fourth value has no cell and the consolidation buckets it as `ok` or `no-evidence`, which kills the distinction in the merge instead of in the domain. An annotation on a status that already counts survives the roll-up.
- **Fixes touch code**, not only docs: a required region key with startup validation, a redaction step in the shared call path, a lifecycle rule, a deletion path and its test. The domain gate is the target's own test suite plus whatever the pinned-region validation needs to keep passing. Two of the fixes are documents rather than code - the map and the register - and they are the two the audited team has to own, so the plan says who.
- **Cross-links:** `security/sensitive-data` for the call-site half of the trail claim; `deps/inventory` for why the package graph is not the provider list, since a provider reached over HTTP never enters it; `eval-audit` for redaction as a dimension; `ci/permissions-secrets` for pipeline credentials, which are not where a request lands.

### The deliverable

The **sub-processor inventory** #4 asks for is an opt-in *deliverable*, declared in `SKILL.md` prose rather than as a record. `audit/SKILL.md` keeps deliverables out of a sweep whatever the user answers, because each is an artifact *of* the audited project rather than findings *about* it, and producing one on the strength of a diagnosis nobody has read yet is the writing a report-only run exists not to do. It is offered as a per-domain follow-up, and it is rendered from `provider-surface`'s derivation rather than from a fresh pass, so the inventory and the finding cannot disagree.

### Blast radius outside the new skill

Nine files assert the domain count or a list that this change falsifies. None is caught by a gate except the two tests.

| File | What changes |
|---|---|
| `.agents/skills/audit/SKILL.md` | The domain list in the `description` frontmatter and in the body's opening paragraph; "eight domain agents" twice; "the other seven domains" (arithmetic, not a list, so it becomes eight). Plus two new bullets carrying the personal-data declaration - one in step 0 that resolves it, one in the fan-out brief that passes it - which landed with the Task 1 review fixes rather than in the count sweep, because the domain skill's applicability rule is wrong until they exist. |
| `.agents/skills/audit-core/SKILL.md` | The domain list in the `description` frontmatter only. "Measured across the eight migrated domains" is a record of a measurement over the eight that were migrated and stays as written; re-numbering it would claim a measurement nobody took. |
| `README.md` | "Eight domains, 69 check records" - both numbers recomputed at write time, neither carried. |
| `CLAUDE.md` | "eight `<domain>-audit` skills". |
| `docs/audit/handbook-traceability.yaml` | The nine row changes in the table above, plus the gap note on `observability/capture-per-subagent-per-tool-usage` reading "not one of the eight skills declares a check", which gets **de-numbered** rather than re-numbered, the way the "six checks" note was. |
| `docs/audit/handbook-traceability.md` | Regenerated, never edited. |
| `docs/audit/sweep-obligations.md` | Read after touching either engine file: `tests/test_sweep_obligations.py` fails on an anchor that no longer occurs exactly once or a quotation that is no longer verbatim. |
| `tests/scripts/test_audit_checks.py` | `test_the_real_checks_tree_covers_every_domain` gains `data-protection`; `test_the_real_checks_tree_loads_clean` gains the eight ids. Both assert exact sets on purpose - do not weaken either. |
| The plugin | `claude plugin details handbook-audit` should report one more skill than it does now. Verify by reading the count, since `claude plugin validate` passes on a plugin that discovers none. |

### Voice and constraints

Records and skill files follow the family's register: the claim as lead prose, then `## Severity`, `## Tooling fallback`, `## Fix`, `## Review lens`, omitting a section the check has nothing to say in, and every review-lens paragraph opening `**Label** - `. Links from `.agents/skills/` to files in this repository are absolute GitHub URLs, because the skills run from a plugin cache where a relative path resolves to nothing; that rule is scoped to `.agents/skills/` and does not reach anything under `docs/`. No em-dash in this spec or the plan. Never assert a count without computing it in the same breath.

## Verification

- `uv run python scripts/render_handbook_traceability.py --check` passes, which is what enforces both directions of every edge above.
- `uv run pytest tests/ -q` passes, including the two exact-set tests and `test_sweep_obligations.py`.
- `uv run ruff check .` and `uv run ruff format --check .` pass.
- `uv run python scripts/render_handbook_artifact.py` still builds, since the matrix is not its input but the handbook it renders is unchanged.
- `claude plugin details handbook-audit` reports the new skill.
- The gap list in the regenerated matrix shows five fewer `unchecked` entries in the `data-protection` rows and four `residue` entries that were not there before, and the per-band kind split line reflects it.
- A reading pass over the eight records against the eight dimensions in #4, and against the gap note each row carried, since no gate compares a record to the prose that justified it.

## Acceptance criteria, mapped

#4's five criteria against this design:

1. *A privacy/data-protection lens exists on `audit-core`* - the skill plus eight records.
2. *Provider DPA, GDPR-compliance and residency checks over every sub-processor touching personal data* - `processor-register` and `provider-surface` for the register and its reconciliation, `residency-pinning` for where the request lands.
3. *PII-minimization, retention/deletion, and PII-in-logs/artifacts dimensions* - `boundary-minimization`, `retention-limits` and `deletion-path`, `stored-artifact-pii`.
4. *Sub-processor inventory as a deliverable; severity rubric with EU/GDPR context* - the opt-in deliverable above; the rubric is inherited from the matrix rather than invented, since four of the rows are `critical` on the matrix's own test and the records take their severity from the rows they ground.
5. *Cross-links `security-audit` and the model/provider supply-chain issue* - the cross-links section above, and `provider-surface` records that #6 consumes its derivation.

## Open questions

None outstanding. The tooling question above was resolved by research before implementation began; the resolution is recorded in the design section rather than left here, since it is now a decision rather than a question.

## Related

- #47, handbook Part 10, which this issue verifies. Merged as `14762bb`.
- #6, model and provider supply chain, which consumes `provider-surface`'s derivation rather than re-deriving it.
