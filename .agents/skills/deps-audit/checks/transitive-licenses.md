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
  typescript: [license-checker]
---

# Transitive-license deep dive

Full graph, not just direct - default on for published libraries, ask otherwise.
