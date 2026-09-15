---
id: data-protection/processor-register
domain: data-protection
locality: global
handbook:
  - data-protection/every-processor-needs-an-agreement-and-the-register-must-match-the-code-a
  - security-supply-chain/depend-only-on-what-you-can-account-for-b
---

# Processor register

Whether a register of processors exists and records, per processor, a signed data processing agreement, the provider's position on training - and, where the provider's default is that it does train, the mechanism the project opted out by - and the retention window including any longer abuse-monitoring one, plus the date the register was last reconciled against the code, without which a register nobody has ever checked and a register that matches the code look identical from outside.

## Severity

The two bands about a **missing register** rest on personal data crossing to the third party, sourced the way `SKILL.md` fixes it rather than inferred, and drop one level where nothing establishes it. The bands about a **field the register itself omits** - a missing retention window, a missing reconciliation date, a value recorded as free prose - are mechanism bands and stand whatever established the surface: the register's own entry declares that party a processor, which is at least as strong as the operator's declaration, and the finding cites a field absent from a document rather than a payload in a store.

**Critical** - no register at all, or a register with no DPA field, where the code reaches a third party and an artifact establishes that personal data crosses to it. Both halves of that condition are sourced, and neither is an impression. The **reachability** half comes from the derived personal-data surface `SKILL.md` builds once in `audit-core` step 1, not from `data-protection/provider-surface`'s output, which is not available to this agent. The **crossing** half comes from what `SKILL.md` says establishes a surface.

**Important** - the same register gap where the code reaches a third party and nothing documents what crosses to it. Report an unregistered processor whose payload is undocumented, which is true and actionable, rather than an unaccounted transfer of personal data, which is the row `SKILL.md` withdraws.

**Critical** also for a processor recorded with no retention window - a mechanism band, per the rule above. Part 10 makes that the test: a provider whose retention window you cannot state is a provider you have not accounted for, which is Part 9's dependency test asked about data instead of about code. This band is why the record also grounds Part 9's own AI-surface row, whose claim asks for exactly this: the pinning half of that row is `eval/reproducibility`'s and the retention-terms half is read here.

**Important** - a register whose fields are all present but which records no reconciliation date, so nobody can say when it last matched the code. The fields are the easy half; the date is what makes the register a claim about the current system rather than about the day it was written.

**Minor** - a field recorded as free prose where a date or a yes/no would be checkable: "we opted out" without the mechanism, "short retention" without a window. The fact may well be right, and nobody downstream can act on it or notice it going stale.

## Tooling fallback

No tool enumerates a project's processors or reads a contract, so this is a reading pass. Read the register wherever the project keeps it - a compliance or privacy directory, a vendor or sub-processor page in the documentation tree, an architecture decision record - and then, per processor it lists, whether the three fields Part 10 asks for are present and dated rather than gestured at.

**The hard boundary, which is the rule this domain breaks most easily:** whether an agreement was actually signed, and whether a provider honours the retention window it publishes, is not visible from a repository at all. A register can name a DPA that was never executed, and the file reads the same either way. So report each of those as an annotated status in the form `SKILL.md` fixes, naming what would settle it and who holds that evidence: the executed agreement, held by whoever owns compliance, and the provider's current terms, held by the provider. Never `ok`. This record is where `SKILL.md`'s rule for choosing between the two bites, so apply it here rather than picking: a register that **records** an agreement is `warn (unverifiable-from-here)`, because the clone read the record and cannot read its truth, while a register with **no agreement field** is a plain `violation` with no annotation, because the clone settled it and annotating it would report an open question the repository already answered. The register's *contents* are readable here and its *truth* is not, and the reconciliation date is in this check because it is the one field that makes the gap between them visible from the clone.

Keep the terms of art apart while reading, because the section fixes them and a report that conflates them misdirects the fix: the **legal basis** for the processing is the controller's own and is a separate obligation, so a register missing a basis is not a finding of this check. This check is the processor's agreement, its training position and its retention window.

## Fix

Create or complete the register with the three fields per processor plus a reconciliation date, and expect the enumeration to be most of the work: the real list is longer than the one a team writes from memory. It includes the hosting and managed-database vendors underneath everything, and the three that get forgotten because they receive prompts rather than documents - tracing and observability backends, error trackers, eval platforms. A prompt carries whatever personal data the task put into it, so a tracing vendor that stores prompts is processing personal data exactly as the model provider is.

The audit can supply the list of who is called, from `data-protection/provider-surface`. The audited team owns the contract facts, because they are not in the repository and no audit can put them there, so name that owner in the remediation plan rather than leaving the row addressed to nobody.

## Review lens

**Evidence boundary** - every claim in the row is separated into what the repository showed and what it cannot show, and no unverifiable item is reported as passing. A row asserting that a DPA is in place has confused the register's record of an agreement with the agreement.

**Term precision** - the row is about the processor's agreement, its training position and its retention window. Never the controller's legal basis, which is a different obligation and not the audited project's vendor paperwork; and never the lawful transfer route, which belongs to `data-protection/residency-pinning` and its own row, so a transfer-route claim here has no band to land in and duplicates that check.

**Enumeration provenance** - a processor the row reports as unregistered is cited from the derived personal-data surface rather than named from the auditor's own reading, so this row and the derivation cannot disagree about who is called.
