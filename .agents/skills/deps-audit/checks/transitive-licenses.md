---
id: deps/transitive-licenses
domain: deps
locality: global
optin: true
handbook: []
handbook_note: >-
  The handbook's clause already asks to know the third-party surface
  transitively, and deps/licenses covers that baseline; this check is the
  opt-in full-graph depth pass beyond that baseline, not a distinct clause, so
  the handbook states no separate deeper-graph requirement to ground it
  against.
tooling:
  python: [pip-licenses]
  typescript: ["pnpm licenses list", "yarn licenses list", "@cyclonedx/cdxgen"]
needs:
  resolved-tree: [pip-licenses, pnpm licenses list, yarn licenses list]
ungranted_note: >-
  The registry procedure `deps/licenses` describes answers this check too, and the
  extra depth costs nothing: a complete lockfile already pins the transitive graph, so
  the set to query is the whole of it rather than the direct dependencies. It is
  conditional on that lockfile existing - a partition pinning only its direct
  dependencies leaves the transitive set unenumerable without the tree, and that is
  `no-evidence (not-permitted)` rather than a clean result.
---

# Transitive-license deep dive

Full graph, not just direct - default on for published libraries, ask otherwise.

## Tooling fallback

Same tools and same precedence as `deps/licenses`, which its own fallback section states; this check differs in how far down the graph the answer has to hold, not in what produces it. The tools listed there already report the whole resolved graph rather than the declared direct set, so the depth is a property of how the output is read, and a run that answers only for direct dependencies has not run this check.
