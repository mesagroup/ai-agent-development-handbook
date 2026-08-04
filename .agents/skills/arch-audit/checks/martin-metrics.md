---
id: arch/martin-metrics
domain: arch
locality: global
optin: true
handbook: []
handbook_note: >-
  A quantitative restatement of the god-module and over-abstraction axes
  rather than a clause of its own; the handbook states neither the metric nor
  a threshold for it.
tooling:
  python: [grimp]
---

# Package stability metrics (distance from the main sequence)

Compute Robert C. Martin's package metrics from the graph artifact: afferent/efferent coupling (`Ca`/`Ce`), **instability** `I = Ce / (Ca + Ce)`, **abstractness** `A = abstract types / total types`, and **distance** `D = |A + I − 1|`. High `D` flags the two rigid corners - a **concrete package everyone depends on** (painful to change) and an **abstract package nobody uses** (needless, the formal statement of over-abstraction). This is the quantitative version of the god-module and over-abstraction axes unified in one metric; it is a heavier, more academic pass, so it is opt-in - enable via argument or ask the user, and default off for a quick pass.

## Tooling fallback

**Python** - from the graph artifact built for layering (`grimp`), per package: afferent coupling `Ca` (the packages that depend on it), efferent coupling `Ce` (the packages it depends on), **instability** `I = Ce / (Ca + Ce)`, **abstractness** `A = abstract types / total types`, and **distance** `D = |A + I − 1|`. Record `Ca`, `Ce`, `I`, `A` and `D` per package; `D` is the evidence.

**With `grimp` unavailable** - every input is already to hand: `Ca` and `Ce` are in-degree and out-degree over the same edge set the layering check built, and `A` needs one pass counting classes per package and how many of them are abstract (an `ABC` base, a `Protocol` base, or any `@abstractmethod`). No dependency is required to compute any of the five numbers.
