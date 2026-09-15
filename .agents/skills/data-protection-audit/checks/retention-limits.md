---
id: data-protection/retention-limits
domain: data-protection
locality: global
handbook:
  - data-protection/retention-and-deletion-are-design-decisions-not-cleanup
---

# Retention limits per store

Whether every store that holds personal data carries a retention limit somebody chose on purpose, with something enforcing it - a TTL on the record, a lifecycle rule on the bucket, or a scheduled job with a test - as against a period written down and enforced by nothing, which is a policy rather than a retention limit and leaves the data exactly where it was.

## Severity

The bands that assert personal data is being kept past its limit rest on personal data resting in the store in question, and that condition is sourced the way `SKILL.md` fixes it rather than inferred: the operator's declaration at scope time, a store the data-flow map names, or an artifact that plainly carries personal data - an authentication table, a bucket of uploaded documents, an index built over customer files. Where none of those establishes it, **that band drops one level and the row reports the store as unbounded with its contents undocumented** - a store nothing expires is a true finding whatever is in it, while the same row called Critical asserts that personal data has been retained indefinitely on the strength of a table name, which is what `SKILL.md` withdraws rather than downgrades. The bands about the enforcement mechanism - an untested job, a limit documented and enforced by nothing, a limit nobody stated - are about the mechanism rather than about a payload, so they stand whatever established the surface, which leaves the Critical below as the one band the drop rule reaches.

**Critical** - a store holding personal data with no limit anywhere: none in the schema or its migrations, none in the infrastructure definition, none in a scheduled job. The limit is the decision that gets cheaper the earlier it is made, and this band is what makes that concrete: at creation time you know what is in the store and why, and at every later moment you do not, so an unbounded store accumulates the data and the difficulty of deciding what to do with it at the same rate.

**Important** - a limit that is documented and unenforced. A period in a policy document, a privacy notice or a design note, with nothing in the store that expires anything, is a statement of intent. Report the document as evidence of the limit somebody intended and the enforcement as absent, so the fix is read as the mechanism rather than as the paragraph, which is already written.

**Important** also for a limit enforced by a scheduled job with no test. Nothing tells you the day it stops running: a job that fails silently leaves a store that looks bounded and is not, and the gap surfaces only when somebody asks how old the oldest record is - which is usually the same day they ask for it to be gone.

**Minor** - a limit that is enforced but stated nowhere a reader can find, so nobody can say whether it was chosen or inherited from a library's or a platform's default. The value may well be right, and the row is that a limit nobody can find is one nobody can review, defend to a data subject, or change deliberately.

## Tooling fallback

No tool decides this check, and the reason is structural rather than a fact about which scanners exist: a retention limit is a number somebody chose for a reason, and no scan separates a TTL set on purpose from one that arrived with a client library's default. So this is a reading pass over an enumeration this domain already has rather than a fresh one.

**Take the store list from the store axis of the derived personal-data surface `SKILL.md` builds once in `audit-core` step 1**, under the engine's rule that a shared ground-truth artifact is built once and consumed rather than rebuilt inside each agent. Take it from that artifact and **not** from `data-protection/data-flow-map`'s output, which is not available to this agent. `SKILL.md` names that axis's evidence, and the stores it has to reach past the one a service is named after are those that arrive as an implementation detail of something else: a cache, a vector index, an object bucket of uploads, a queue, the log and trace retention on an observability backend, and the backup schedule.

Then read, per store, where a limit would live: a TTL or expiry column in the schema or the migrations; a lifecycle or expiration rule in the infrastructure definition; a retention setting in a managed service's configuration; or a scheduled job in the CI or scheduler configuration, together with the test that says it still runs. Where a store carries a limit, read what the limit applies to as well as its value, because a lifecycle rule that expires one prefix of a bucket says nothing about the rest of it.

**A provider's own retention window is not this check's field.** How long a model provider, a tracing backend or an error tracker keeps what was sent to it is `data-protection/processor-register`'s. This check is the stores the project itself operates. Reporting the provider window in both rows counts one gap twice and splits its fix across two owners.

**The other half of this section is `data-protection/deletion-path`'s**, so the boundary has to be said rather than assumed. This check reads whether a limit exists per store and what enforces it: time-based expiry that runs without anyone asking. That check owns the deletion path. A store can fail both, and they are two gaps with two mechanisms, so say which one a row is about. The backup schedule's **window** is a retention limit and belongs here, while its **aging out** is the downstream boundary, so the missing window is reported once, in this row.

**The audit reads the mechanism; it never runs it.** Triggering a purge job or a lifecycle rule to see whether it still works removes everything already past the cutoff, which is the destruction the fix below refuses to make on the audit's initiative, reached by the back door. The evidence is the configuration and the test; where those do not settle whether the job still runs, the row says the enforcement is unverified rather than proving it.

**Where the repository plainly provisions a store somewhere else** - a managed service created by hand, a platform whose retention is set in a console - there is no configuration in the clone to read, so say so as a limit of the pass rather than reporting the limit as absent. Status then follows `SKILL.md`'s rule for choosing which one carries the annotation: where the repository documents that the limit is set in that console, the clone read the record and cannot read its truth, which is `warn (unverifiable-from-here)` naming the platform's configuration and whoever operates it as what would settle it. Where nothing documents a limit at all, the absence of a chosen and stated limit is itself readable and the bands above apply with no annotation. This is available only where the repository plainly provisions the store elsewhere; it is not a softening for every missing limit, because a store the infrastructure definition creates and does not bound is a readable absence that the clone has already settled.

## Fix

Choose the limit when the store is created, which is when you know what is in it and why, and enforce it in the mechanism the store already has - preferring a TTL or a lifecycle rule over a job, because a job can stop running and neither of those can. Where a job is the only mechanism available, ship the test with it in the same change, since the job and the test are one fix rather than a fix and a follow-up.

**Applying a limit to a store that already exists is itself a deletion, and it is not the audit's to make.** The mechanism's first pass removes everything already past the cutoff, which on a store years old is most of what it holds. So the remediation names that as a decision for whoever owns the data - what happens to the existing records, whether anything has to be exported or reviewed first, and what date the limit starts counting from - and what lands is the mechanism plus that decision, never a lifecycle rule applied on the audit's initiative and left to run.

## Review lens

**Enforcement evidence** - a limit is reported as enforced only where the row cites the mechanism at a `file:line` in the target, expressed relative to `target_root` rather than to any scratch copy: the TTL definition, the lifecycle rule, or the scheduled job together with its test. A documented period is never that citation, because from the data's point of view the two look identical and only one of them expires anything.

**Store coverage** - the row says which stores were enumerated and where the enumeration came from, and names the ones whose configuration the pass could not read, so a store nobody looked at is visible as unexamined rather than counted as bounded or as absent.

**Scope with the register** - the row is about the stores the project operates. A provider's own retention window is `data-protection/processor-register`'s field and has no band here, so a claim about how long a provider keeps a prompt belongs in that row and not in this one.

**Non-destructive remediation** - no row here recommends deleting data or dropping a store, and a row proposing a limit on an existing store names the decision about what is already past it rather than leaving it to the mechanism's first run.
