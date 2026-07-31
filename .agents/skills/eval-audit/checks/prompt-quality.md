---
id: eval/prompt-quality
domain: eval
locality: local
handbook:
  - evaluation/measure-the-behaviors-that-matter-a
---

# Prompt / SOP quality

The *behavioral* facets: drift between prompt and the current code/tools, missing versioning/changelog, and **injection-resistance** (does the prompt hold under adversarial/tool-returned input). The *static* authoring facets (spec-conformance, RFC 2119 constraint hygiene, contradictions/dead instructions, cognitive load, redundancy) are **`prompt-audit`**'s - run it alongside this one for a prompt change and defer those rows there.

## Severity

**Important** - a prompt that contradicts the code or has drifted.

## Tooling fallback

**Prompt audit:** read each system prompt / SOP / tool description; check against the current code/tools for drift (references to tools/steps that changed or vanished) and for injection-resistance (how untrusted/tool-returned content enters the prompt). For the *static* authoring quality (spec-conformance, constraint hygiene, contradictions, cognitive load, redundancy), hand off to `prompt-audit`, which drives the `/prompt-analyzer` scan and the SOP-spec checks; don't duplicate them here.

## Fix

**Prompt fixes:** remove contradictions/dead instructions, reconcile the prompt with the current tools/code, add versioning + a changelog entry explaining *why* the prompt changed (keep prompt changes in their own commit if the project's convention says so), and harden injection-resistance.

## Review lens

**Prompt correctness** - prompt edits preserve intended behavior (re-evaluated), match the current tools/code, and don't introduce new contradictions or injection weaknesses.
