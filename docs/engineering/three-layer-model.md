# Part 6 — The Three-Layer Document Model

Lidia is a platform for working with documents — contracts, judgments, legislation, expert reports, evidence transcripts — through AI agents. The single most important architectural idea in that work is that document knowledge splits into **three layers with different reuse profiles**, and that keeping them explicit is what makes the whole system diagnosable, reusable, and separately evaluable. This page is the *why it's generic and why it helps*; the implemented surface is documented in the [three-layer knowledge-model story](../stories/2026-06-15-three-layer-knowledge-model.md) and the [document_model architecture](../architecture/capabilities/document_model/).

## Why: a document has no privileged decomposition

The instinct, inherited wholesale from computer science, is to model a document type once — enumerate its fields, define them, done — and reuse that schema forever. It works for regular documents and stalls everywhere else, because it assumes the world carves cleanly at stable joints. A document is not a thing with one true structure waiting to be read off. The same contract decomposes differently depending on whether you are checking enforceability, computing tax exposure, or screening for fraud. There is no view-from-nowhere schema that captures "everything important," because importance is relative to a question.

But — and this is the part that keeps the idea from collapsing into "everything is bespoke" — **the reusable core is real.** Two strata genuinely generalize. The artifact's *intrinsic structure* (pages, tables, reading order) is fully reusable: every document is a document at this level. And a thin, stable vocabulary of the *entities a domain keeps reusing* (a contract's parties and governing law, an invoice's amounts and dates) is partially reusable. Conceding those is not a retreat. What stays use-relative is only the *task* layer: the decomposition a specific workflow needs. The universal-schema instinct is right about the core and wrong about the task layer, and the three-layer model is exactly that boundary drawn in the architecture.

## What: the three layers

| Layer | What it answers | Reuse profile | Epistemic status |
|---|---|---|---|
| **Layer 1 — intrinsic structure** | What is physically on the page: pages, blocks, tables, reading order, sections, signatures. Domain-free, engine-detectable. | **Fully reusable** — modeled in advance. | **Perception** |
| **Layer 2 — domain entities** | What the document is about, in domain terms: parties, dates, citations, obligations. Domain-shaped but reusable across workflows. | **Partially reusable** — a sparse upper vocabulary each domain extends. | **Grounding** |
| **Layer 3 — workflow knowledge** | What *this* workflow needs to conclude: "is this citation correct?", "what's the indemnity cap?", "summarize for the board." | **Not reusable, and should not be** — built when a task runs. | **Inference** |

The model is domain-general: the layers fall out just as cleanly for an invoice as for a novel. Perception, grounding, and inference are three genuinely different questions, not three degrees of one.

## The rule: never skip a layer

The seductive shortcut in document AI is to drop the raw document (or a text dump of it) into the prompt and ask the final Layer-3 question directly, letting a capable model sort out the rest. It works in a demo and fails in production, because the three layers are three distinct places a mistake can happen, and the shortcut collapses them into one opaque call: a misread table cell (perception) becomes an amount attached to the wrong party (grounding) becomes a wrong contractual conclusion (inference).

The cost is not just the error; it is that the error is **undiagnosable.** With the layers explicit, each step is separately inspectable and a failure is localizable to one layer. Skip them and you cannot answer the only question that matters when the answer is wrong: *which layer failed?* A layered system fails in a place; a skipped-layer system just fails. (Going back to re-read a specific span that the lower layers point to is not skipping a layer — it is using them to navigate. What the rule forbids is the ungrounded one-shot from raw document to final answer.) In practice the rule is most often violated by Layer 3 trying to short-circuit Layer 1 — "extract the parties from this raw markdown" — and it is worth re-explaining at the code review of every new agent.

## The contracts that make layering pay off

Layering is only worth the cost if a few contracts hold. These are the load-bearing engineering decisions.

### Engine-agnostic intermediate representation (an anti-corruption boundary)

Document text does not arrive as structure; it arrives from an extraction engine, and there are several worth using (AWS Textract, Docling, Mistral OCR), each with an incompatible output schema. Wiring chunking, grounding, and retrieval directly to one engine's format means writing the adapter twice — once now, and again the day the engine is upgraded or a second is added. So Layer 1 is a single engine-agnostic IR (typed blocks, a containment hierarchy, provenance on every block), populated by a thin per-engine *builder*, with everything downstream reading the IR and never the raw engine output. This is a classic anti-corruption layer: the IR is the one stable contract, engines vary above it, consumers vary below it, and neither side's churn reaches the other. Engine identity lives in the metadata, not the block shape — a Textract paragraph and a Docling paragraph are indistinguishable at the schema level. See [builders](../architecture/capabilities/document_model/builders.md) and the [Mistral OCR engine](../architecture/capabilities/document_model/mistral-ocr-engine.md).

### Stable, content-derived identifiers (the identity contract)

Layering pays off only if the lower layers hand the upper layers something *stable* to point at. Layer 2 grounds entities against Layer 1 structures; Layer 3 draws conclusions against Layer 2 entities; both are annotations on identifiers below them. If those identifiers churn every time the document is re-extracted, the annotations dangle and the structure collapses back into re-extract-everything, defeating the reuse the model was built for. So every block gets an identifier derived from its *content*, not its position — the same content yields the same id across re-extraction and across builder-version bumps.

The guarantee has a precondition that is easy to wave away: two engines almost never produce character-identical text for the same passage (one resolves a ligature, another de-hyphenates a line break, a third emits different whitespace). *Canonicalization* — a normalization pass before hashing — is what makes the guarantee real for benign drift. What it cannot do is manufacture agreement that isn't there: if an engine genuinely segments the page differently, the canonical text differs and the id changes, correctly. So cross-engine stability is not a property of the hash; it is an *alignment* problem (the classic record-linkage task): match new blocks to old by content, structure, and provenance, and carry the old ids forward. The hash gives identity *within* an extraction; alignment gives it *across* extractions.

### Versioned, additive enrichment over an immutable base

Once Layer 1 is a stable base, the refinements built on it (section synthesis, footnote linkage, figure detection, reading-order repair) run as *versioned, additive enrichment passes* over that base, not folded into extraction. Each pass reads the base (and, if it likes, earlier passes' output), writes annotations keyed by the stable block ids, and stamps its output with its implementation identifier plus version. The payoff: improvement stops meaning re-extraction. Improve the footnote linker and you re-run one pass over an unchanged base and diff its output, leaving the base and every other pass untouched. This is the immutability lesson from data systems — keep an immutable base and derive recomputable views from it rather than mutating the source. Re-extraction is reserved for the rare event that actually changes the base: a different engine, a version bump, or a fix in the base builder. See the [document post-processing framework](../architecture/capabilities/document_model/document-postprocessing.md) and [enrichment passes](../architecture/capabilities/document_model/enrichment-passes.md).

### Keep Layer 2 sparse, keep Layer 3 disposable

The standing temptation is to let Layer 2 grow: a workflow needs a derived fact, computing it once in the shared layer feels efficient, and a workflow-specific convenience quietly migrates down. Every such migration erodes the one property that made Layer 2 worth sharing — its reusability. The test is what *kind* of thing it is: a task-independent, stable domain fact belongs in Layer 2; a task-shaped *judgment*, whose definition depends on the question, stays in each workflow's Layer 3, even when two workflows overlap and it looks like duplicated effort. Hoisting a task-shaped judgment into Layer 2 to deduplicate bakes one workflow's assumptions into the shared layer and couples the two.

## What layering unlocks: typed tools over one fuzzy lookup

Once a document is layered (Layer 1 structure with stable ids, Layer 2 resolved entities), an agent can compose *precise, typed* operations over it instead of one similarity search: structural navigation ("read everything under section 3.4"), clause search ("all clauses about change of control"), entity-in-context ("every mention of Acme Srl"), and semantic search over clean, anchored units — each optionally following resolved references to pull in richer context. The raw-text-dump baseline collapses the layers and forfeits every one of these, leaving only fuzzy retrieval. The agent's job becomes *choosing and composing the right tool for the question* rather than hoping one vector search suffices — which is the operational reason the layers were worth building, since the apt decomposition is relative to the question. Every tool rests on identifiers that survive re-extraction; if they churn, every tool above them breaks.

## Why this is the organizing principle, not just a document feature

The same shape recurs one level up, in [how the codebase is structured](codebase-structure.md): a reusable core (`core/`, lower-layer `capabilities/`) that is modeled in advance, and task-shaped `agents/` built per workflow. "Keep the reusable core sparse and stable; keep the task layer rich and disposable" is the document-model rule and the module-dependency rule at once. And because the layers are separable, they are separately *evaluable* — a golden dataset per layer, far less noisy than one ill-defined end-to-end number ([Part 5](evaluation.md)). Diagnosability, reuse, and measurability are three payoffs of the same decision: make the layers explicit and never skip one.

## See also

- [Three-layer knowledge-model story](../stories/2026-06-15-three-layer-knowledge-model.md) — the half-time report on the implemented Layer 1
- [document_model architecture](../architecture/capabilities/document_model/) — builders, enrichment passes, schema, rendering
- [Knowledge extraction strategy](../research/lidia-knowledge-extraction-strategy.md) — the originating strategy doc (background)
- Handbook: [Part 2 — Codebase structure](codebase-structure.md) · [Part 5 — Evaluation](evaluation.md)
