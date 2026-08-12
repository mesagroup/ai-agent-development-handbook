# Part 10. Data protection & privacy

*The previous part keeps the machine safe from whoever attacks it. This one keeps the data lawful for the people it belongs to, which is a different obligation with a different subject: the risk here is the system working exactly as designed, shipping personal data somewhere it may not be. It stands over every change alongside Part 9, and it reaches back into the trail and the datasets the earlier parts asked you to keep.*

Part 9 asks what an attacker could do to your system. This part asks what your system does to the people whose data passes through it, and the two questions have almost disjoint answers. An agentic product makes the second one sharper than most: the trust boundary is crossed on every model call, so personal data leaves your control as a matter of routine rather than by accident, and the artifacts the rest of this handbook asks you to keep are themselves stores of personal data that nobody set out to create, the run trail ([Part 6](observability.md)), the eval dataset built from real inputs ([Part 7](evaluation.md)), the decision trail ([Part 8](documentation.md)). Where you operate under a data-protection regime ([GDPR](https://eur-lex.europa.eu/eli/reg/2016/679/oj) and the like), that posture has to be demonstrable rather than merely intended, and the thing you have to demonstrate it with is the repository.

This part is engineering, not legal advice. It states what to build and maintain so the legal question has an answer, and it says plainly which half of each answer no repository can settle. Take that half to whoever owns compliance where you work; the point of the half you can settle is that they should not have to ask you for it twice.

## Know what personal data you hold, and where it goes

Keep a **data-flow map** beside the code and maintain it with the code. It answers three questions and nothing else. Where does personal data **enter** (uploads, form fields, integrations pulling from a customer's system, and whatever a user types at an agent)? Where does it **rest** (the primary store, the object store, the vector index, caches, logs, eval datasets, backups)? And what are the **outbound edges** that leave your trust boundary, with what crossing each one? A data-protection regime knows this artifact as records of processing. Where compliance keeps one and engineering keeps none, what compliance has is a snapshot of what the system did on the day somebody last asked.

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
app -> b -> p: model, search, OCR, tracing
```

## Every processor needs a legal basis, and the register must match the code

Every third party that sees personal data on your behalf is a **processor**, and each one needs a basis you can produce on request. Enumerating them is most of the work, because the real list is longer than the one a team writes from memory: the model and LLM APIs, but also search providers, OCR, extraction and transcription services, the hosting and managed-database vendors underneath all of it, and the three that get forgotten because they receive *prompts* rather than documents, namely tracing and observability backends, error trackers, and eval platforms. A prompt carries whatever personal data the task put into it, so a tracing vendor that stores prompts is processing personal data exactly as the model provider is.

Record three things per processor. A signed **data processing agreement**. Whether the provider **trains on your data**, and where the default is that it does, that you have opted out and by what mechanism. And the **retention window**: how long the provider keeps your inputs and outputs, including any separate window for abuse monitoring, which is often longer than the one advertised for the service itself. A provider whose retention window you cannot state is a provider you have not accounted for, which is the test [Part 9](security-supply-chain.md) applies to any dependency, asked about data instead of about code.

Then the half that is yours to enforce: **reconcile the register against what the code actually calls.** Derive the provider list from the repository, from the SDK imports, the configured base URLs, the MCP servers and tool endpoints, and the credentials the deployment carries, then compare it with the register. A provider reachable from the code and missing from the register is a finding, and it is the only half of this question a repository can settle. Whether the agreement was signed, and whether the provider honours it, is not visible from here at all. Keep the two apart whenever you report on this, because a register nobody has ever checked against the code and a register that matches it look identical from the outside.
