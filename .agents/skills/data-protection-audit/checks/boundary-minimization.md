---
id: data-protection/boundary-minimization
domain: data-protection
locality: local
handbook:
  - data-protection/minimize-before-the-boundary
routes:
  - lang: any
    kind: procedure
    note: >-
      No tool decides whether a payload was minimized, because the question is what a value means rather than what shape it has, so this is a reading pass; and it is `local` because the outbound call path is, so a service that redacts beside one that does not is the finding rather than an average that describes neither. Read the outbound client layer or middleware every request goes through, and its absence where there is none, which is itself what the shared-path band reports. Read the individual call sites, to see whether the step is shared or repeated - and take the outbound edges from the derived personal-data surface `SKILL.md` builds once in `audit-core`'s parallel evidence step, restricted to this partition by the partition each entry records, rather than enumerating providers again here, so this row and the rest of the domain cannot disagree about which edges exist.

      **Follow the outbound call into the package that makes it before concluding minimization is absent.** Where this partition reaches a provider through a shared client in another partition, the shared step is present and the shared-path band does not apply; say which partition holds it. `SKILL.md` gives the reason: a shared client in a `core` package that every service imports is the state this check's own fix asks for, so a per-partition agent that reads only its own directory reports the repository that already did the work as the one that did not. Read the eval suite for a dimension that measures the redacted path against the unredacted one.

      **Hand the measurement half off rather than absorbing it.** `eval/coverage` owns whether a behaviour that matters has an eval exercising it at all, so a project with no eval suite is that check's finding rather than this one's, and this row reports the missing redaction dimension rather than the missing suite. Note the handoff in the report.

      Personal data reaching a log or an exception message at one of these call sites is `security/sensitive-data`'s row rather than this one's; this one reads the call site for what it sends across the boundary. Do not restate its findings here, and do not accept a clean result from it as covering this check - a call site it cleared for logging still sends an unminimized payload if nothing redacts before the request.
---

# Minimization before the trust boundary

Whether personal data is redacted, pseudonymized or truncated before it crosses the trust boundary, with the step in the one shared outbound call path rather than repeated at each call site - and whether the quality cost of that step is measured rather than assumed away in either direction.

## Severity

The two bands about **no minimization at all** rest on personal data crossing the path, sourced the way `SKILL.md` fixes it, and the first drops to the second where nothing establishes it. The bands about **where the step sits and whether its cost was measured** - per-call-site placement, an unmeasured quality cost, a documented bypass - are mechanism bands and stand whatever established the surface: each cites the shape of the code or the absence of an eval dimension rather than a payload.

**Critical** - no minimization anywhere on an outbound path, where personal data crossing that path is *established by an artifact* rather than assumed: the data-flow map's edge, the operator's declaration at scope time, or a call site plainly handing over user content or an uploaded document. Part 10's reason for putting this ahead of the rest is that the cheapest personal data to protect is the personal data that was never sent.

**Important** - the same absence, on an outbound path where nothing documents what crosses it. An unminimized path whose payload is undocumented is true and actionable; the same row called Critical asserts that personal data left the boundary on the strength of a call to a provider, which is what `SKILL.md` withdraws rather than downgrades, so the row reports the payload as undocumented instead of asserting a transfer.

**Important** - minimization present but implemented per call site rather than in the shared path. Part 10 gives the reason as a prediction rather than as a defect: a call site added next month will not have it. So this band holds even where every call site today is covered, and the finding is the placement rather than a gap you can point at.

**Important** also where redaction is in place and its quality cost is assumed rather than measured, in either direction. Part 10 states the tension outright because both assumptions cost something real: a team that assumes the cost away ships a quality regression under a privacy justification and never connects the two, and a team that assumes it ruinous stops redacting on a hunch. **This band needs an eval suite to exist and to carry no dimension for the redacted path.** Where there is no suite at all, it raises nothing and the report cites the handoff the reading route's note gives instead, because with no suite there is trivially no dimension and a row here would double-report the gap `eval/coverage` owns.

**Minor** - a shared path with a documented bypass for a named case. The bypass may well be the right call, and the row is that its scope rests on prose rather than on construction, so **report it as a path to bound and keep documented, never as one to remove**: an escape hatch somebody needed and lost is replaced by a call site that goes around the shared path altogether, which is the failure this check is about.

## Fix

Move the redaction into the single outbound path, so the next call site inherits it rather than having to remember it. Take the concrete moves Part 10 names, since "minimize" on its own is unactionable: strip the direct identifiers the task does not need; replace them with stable pseudonyms where the agent has to refer to the same person across turns; and send a reference rather than a payload, and an extract rather than a whole document, wherever the task allows it. Where the outbound surface is large enough that no single path exists to move the step into, the fix is to put the outbound calls behind one client layer.

Then make redaction an eval dimension and settle it on the numbers. A redaction the metric survives is free; one it does not is an evidenced trade-off for whoever owns the risk to make, and either of those beats a silent regression or a quiet decision to stop redacting.

## Review lens

**Path coverage** - the finding says whether every outbound call in this partition reaches the shared step, and cites at a `file:line` a call site that bypasses it where one does, expressed relative to `target_root`, so the claim is checkable against the tree the audited team has.

**Cost evidence** - a claim that redaction is or is not costly cites the eval dimension that measured it; where no dimension exists, the row says the cost is unmeasured rather than asserting a direction, because Part 10 names an assumption in either direction as the failure.

**Payload provenance** - a Critical band names the artifact that established personal data crossing the path, and a row with only a provider call under it reports the payload as undocumented at Important rather than asserting a transfer that nothing documents.
