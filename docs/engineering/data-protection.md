# Part 10. Data protection & privacy

*The previous part keeps the machine safe from whoever attacks it. This one keeps the data lawful for the people it belongs to, which is a different obligation with a different subject: the risk here is the system working exactly as designed, shipping personal data somewhere it may not be. It stands over every change alongside Part 9, and it reaches back into the trail and the datasets the earlier parts asked you to keep.*

Part 9 asks what an attacker could do to your system. This part asks what your system does to the people whose data passes through it, and the two questions have almost disjoint answers. An agentic product makes the second one sharper than most: the trust boundary is crossed on every model call, so personal data leaves your control as a matter of routine rather than by accident, and the artifacts the rest of this handbook asks you to keep are themselves stores of personal data that nobody set out to create: the run trail ([Part 6](observability.md)), the eval dataset built from real inputs ([Part 7](evaluation.md)), the decision trail ([Part 8](documentation.md)). Where you operate under a data-protection regime ([GDPR](https://eur-lex.europa.eu/eli/reg/2016/679/oj) and the like), that posture has to be demonstrable rather than merely intended, and the thing you have to demonstrate it with is the repository.

This part is engineering, not legal advice. It states what to build and maintain so the legal question has an answer, and it says plainly which half of each answer no repository can settle. Take that half to whoever owns compliance where you work; the point of the half you can settle is that they should not have to ask you for it twice.

## Know what personal data you hold, and where it goes

Keep a **data-flow map** beside the code and maintain it with the code. It answers three questions and nothing else. Where does personal data **enter** (uploads, form fields, integrations pulling from a customer's system, and whatever a user types at an agent)? Where does it **rest** (the primary store, the object store, the vector index, caches, logs, eval datasets, backups)? And what are the **outbound edges** that leave your trust boundary, with what crossing each one? A data-protection regime asks for a superset of this, which it calls records of processing: it wants the purposes, the categories of people and of data, and the erasure limits as well. The map is the engineering half, and it is the half that goes stale silently. Where compliance keeps a record and engineering keeps none, what compliance has is a snapshot of what the system did on the day somebody last asked.

The map earns its place ahead of every other directive here because each of them is a question asked of one edge or one store. Which providers need an agreement? One question per outbound edge. What gets redacted before it leaves? One question per outbound edge. What carries a retention limit, and what does a deletion have to reach? One question per store. A team that cannot enumerate its edges and its stores is not answering those questions at all; it is answering about the ones it happens to remember, and the ones nobody remembers are where personal data has been sitting longest.

Derive the map from the repository wherever you can, rather than from memory, and keep it where a reviewer will see it go stale: the store a service writes to is in its configuration, and the outbound edges are in its imports and its endpoint config. A map maintained beside the code is falsifiable against the code, which is the property that makes it worth keeping at all.

```d2 title="Personal data crosses the trust boundary on every model call"
direction: right
u: Data subject
app: Your system
b: Minimize at the boundary {shape: hexagon}
p: Third-party processor
s: Your stores {shape: cylinder}
u -> app
app -> s: at rest, under a retention limit
app -> b
b -> p: model, search, OCR, tracing
```

## Every processor needs an agreement, and the register must match the code

Every third party that sees personal data on your behalf is a **processor**, and each one needs an agreement you can produce on request. Keep the term of art straight, because the two get conflated and they fail differently: your *legal basis* is what makes the processing lawful at all, and it is yours rather than any vendor's, while what the processor relationship needs is the contract plus a lawful route for the transfer.

Enumerating the processors is most of the work, because the real list is longer than the one a team writes from memory: the model and LLM APIs, but also search providers, OCR, extraction and transcription services, the hosting and managed-database vendors underneath all of it, and the three that get forgotten because they receive *prompts* rather than documents, namely tracing and observability backends, error trackers, and eval platforms. A prompt carries whatever personal data the task put into it, so a tracing vendor that stores prompts is processing personal data exactly as the model provider is.

Record three things per processor:

- **A signed data processing agreement**, and what it actually permits. "We have a contract" is not the same claim.
- **Whether the provider trains on your data**, and where the default is that it does, that you have opted out and by what mechanism.
- **The retention window**: how long the provider keeps your inputs and outputs, including any separate window for abuse monitoring, which is often longer than the one advertised for the service itself.

A provider whose retention window you cannot state is a provider you have not accounted for, which is the test [Part 9](security-supply-chain.md) applies to any dependency, asked about data instead of about code.

Then the half that is yours to enforce: **reconcile the register against what the code actually calls.** Derive the provider list from the repository, from the SDK imports, the configured base URLs, the MCP servers and tool endpoints, and the credentials the deployment carries, then compare it with the register. A provider reachable from the code and missing from the register is a finding, and it is the only half of this question a repository can settle. Whether the agreement was signed, and whether the provider honours it, is not visible from here at all. Keep the two apart whenever you report on this, because a register nobody has ever checked against the code and a register that matches it look identical from the outside.

## Keep the data where the law lets it be

Personal data stays in a region the law permits, or reaches a destination covered by an [adequacy decision](https://commission.europa.eu/law/law-topic/data-protection/international-dimension-data-protection/adequacy-decisions_en) or by [standard contractual clauses](https://commission.europa.eu/law/law-topic/data-protection/international-dimension-data-protection/standard-contractual-clauses-scc_en), or by one of the other transfer routes the regime allows, binding corporate rules among them. In engineering terms that is one rule with teeth: **pin the region explicitly in configuration, and fail startup when it is unset.** Not a default in your own code either, because a default is what a forgotten configuration line silently resolves to. Required, validated at startup, named in the error when it is missing.

[Part 5](agent-harness.md) asks for the opposite treatment of a model parameter, an optional flag with a provider default, and both are right because the two kinds of value fail differently. A defaulted temperature gives you a run you can inspect, question and redo. A defaulted region gives you a run that already happened in the wrong jurisdiction and looks exactly like one that did not. Sort your configuration by that test: a value whose wrong setting produces a visible, reversible result may default, and a value whose wrong setting produces an invisible, irreversible one must be required. The second kind has no symptom to observe, so it has to be prevented by construction.

Then check the places where residency is actually lost, none of which is the endpoint you remembered to pin:

- **Provider failover**, to another region under load, or a newer model served only from one.
- **A store whose region was chosen once**, at creation, and never revisited: a managed vector index, a queue, a search cluster.
- **Telemetry in another jurisdiction** from the application it watches, which is the common case precisely because nobody thinks of a tracing backend as carrying the payload.
- **Cross-region backups and disaster-recovery replicas**, which is usually the entire point of them.
- **A support workflow that copies a payload onto somebody's laptop** to reproduce a bug: a transfer with no configuration anywhere to pin, so the only control is the process.

## Minimize before the boundary

The cheapest personal data to protect is the personal data you never sent. Redact, pseudonymize or truncate **before** the trust boundary, and prefer sending a reference over a payload wherever the task allows it. The concrete moves, since "minimize" on its own is unactionable: strip direct identifiers the task does not need; replace them with stable pseudonyms where the agent has to refer to the same person across turns; send the extract rather than the whole document where the extract answers the question; and put the redaction in the one call path every request goes through, never at each call site, because a call site added next month will not have it.

State the tension rather than hiding it: **redaction can make an agent measurably worse.** A name stripped from a contract can be the thing that made the clause resolvable; a truncated document loses the paragraph the answer was in. A team that assumes otherwise ships a quality regression under a privacy justification and never connects the two.

So treat it as the first throughline treats any change: a hypothesis, measured. Make redaction an eval dimension ([Part 7](evaluation.md)) and decide it on the numbers, in either direction. A redaction the metric survives is free; one it does not is an evidenced trade-off for whoever owns the risk, and either beats a silent regression or a quiet decision to stop redacting.

## Retention and deletion are design decisions, not cleanup

Give every store that holds personal data a retention limit you chose on purpose, and make something enforce it: a TTL on the record, a lifecycle rule on the bucket, a scheduled job with a test. Then build the deletion path as a feature, before anyone asks for it. Both of these are cheap at the moment you create the store, which is when you know what is in it and why, and expensive at every later moment, which is when you do not.

The part that earns this section is what deletion has to **reach**, because an agentic system spreads copies further than any other kind and almost none of them look like a database row. An embedding of a personal document is personal data; a vector index is a store, and deleting the document does not empty it. So is a cached model response, a stored trace, a run artifact, an eval dataset built from real user documents, a fixture somebody once extracted from a real case because it reproduced a bug, and a backup. A deletion that reaches the primary store and none of those is a deletion in name only. Some of those copies are there because this handbook asked for them, which is why they are the last place anyone looks: the run records are [Part 6](observability.md) doing its job, and a dataset built from real inputs is [Part 7](evaluation.md) doing its job. The rest arrived the way an index or a cache always does, as an implementation detail of something else, which is the other reason nobody has them on a list.

So enumerate the copies while you are creating them, not while you are answering a request. The data-flow map above is the list; the deletion path is the walk over it. If they are the same list, the deletion path is testable, which is the only way anyone can know it works before the day it matters.

## Personal data does not belong in the trail

Logs, traces, error messages, run artifacts and eval fixtures become stores of personal data the moment a payload lands in them, and the payload almost never needs to be there. **Log the identifier you can join back to the record, not the record.** Keep payloads out of exception messages in particular: an exception travels further than a log line, into trackers and alerting channels a much wider group can read, and it is copied into tickets by people who are debugging rather than thinking about data. Build eval fixtures from synthetic or consented data, or from real data put through the same redaction the production path uses, and never from a raw copy of production that nobody minimized.

This is where the handbook's own **capture the trail** throughline meets this part head on, and the resolution is not to capture less. Capture the trail and redact the payload. A record that identifies the run, the shape and size of its inputs, the tools called, the timings, the token counts and the cost is the whole of what [Part 6](observability.md) asks for, and none of it needs personal data in it. What makes a trail diagnosable is that it lets you find the run and reconstruct what happened, not that it quotes the document.

A first-party-code security lens reads for part of this already, at the call site: personal data reaching a log or an error message, and identifiers carried in URLs. What this section adds is the artifacts that outlive the call, the stored traces, the run records, and the eval datasets and fixtures. A lens that reads code does not read those, and they are the copies that persist longest and get shared widest.

## Verify against the real artifacts

This part's obligations are checkable, and the check reads four things. The **register against the outbound calls the code makes**, which is the reconciliation the processor section describes. The **pinned regions against the providers actually configured**. The **retention limits against the stores that actually exist**, taken from the data-flow map rather than from the ones anyone remembers. And a **scan of logs, fixtures and run artifacts** for personal data that reached them. Run it report-only first to see where the repository hurts, then fix one surface at a time in its own reviewed change, which is what [Part 1](lifecycle.md) asks of any audit and what [Part 9](security-supply-chain.md) does with its own surfaces.

One rule makes such a report worth reading, and it is the easiest one to break here: **separate what the repository says is clean from what the repository cannot see at all.** Whether an agreement was signed, whether a provider honours the retention window it publishes, whether a deletion request was carried out downstream: none of that is visible from your code, and none of it becomes visible by failing to find a problem. Name each as unverifiable from here, with what would settle it and who holds that evidence. A report that lists them as passing has not audited them, it has failed to look and said so in the vocabulary of success.

## Checklist: a data-protection sweep

**The map**

- [ ] A **data-flow map** exists beside the code, listing every entry point, every store, and every outbound edge that leaves the trust boundary.
- [ ] It is maintained with the code and falsifiable against it, not a document produced once for an audit.

**Processors**

- [ ] Every third party that sees personal data is in the **register**, telemetry, error tracking and eval platforms included.
- [ ] Each carries a signed **DPA**, a recorded position on **training** (opted out where the default is not), and a stated **retention window**.
- [ ] The register has been **reconciled against what the code actually calls**, and the date of the last reconciliation is recorded.

**Residency**

- [ ] The region is **pinned explicitly in configuration**, required rather than defaulted, and validated at startup.
- [ ] Every destination outside the permitted region is covered by a **lawful transfer route**: adequacy, standard contractual clauses, binding corporate rules.
- [ ] Failover, backups, replicas and telemetry backends checked for the region they actually land in.

**Minimization**

- [ ] Personal data is **redacted, pseudonymized or reduced before the trust boundary**, in the shared call path rather than per call site.
- [ ] The **quality cost** of that redaction is measured as an eval dimension, not assumed in either direction.

**Retention and deletion**

- [ ] Every store holding personal data has a **retention limit that something enforces**.
- [ ] The **deletion path walks the data-flow map**, derived copies included: embeddings, caches, traces, run artifacts, eval datasets and fixtures, backups.
- [ ] The deletion path is **tested**, not merely written down.

**The trail**

- [ ] Logs and traces carry **identifiers, not payloads**, and no payload reaches an exception message.
- [ ] Eval fixtures are **synthetic, consented, or redacted**, never a raw copy of production.

**Standing**

- [ ] The sweep above is run as a **standing check**, and its report separates *clean* from *not visible from here*.

*And the loop begins again: the next idea becomes the next issue. First, a few [closing words](coda.md).*

## See also

- [Part 6. Observability](observability.md), the run records this part treats as a store of personal data.
- [Part 7. Evaluation](evaluation.md), datasets built from real inputs, and redaction's quality cost as an eval dimension.
- [Part 9. Security, dependencies & supply chain](security-supply-chain.md), the other standing obligation, and the provider-as-dependency rule this part's register extends.
- [Part 8. Documentation & knowledge capture](documentation.md), the decision trail, which is a store of personal data whenever a spec or a story quotes a real case.
- [Handbook index](README.md).
