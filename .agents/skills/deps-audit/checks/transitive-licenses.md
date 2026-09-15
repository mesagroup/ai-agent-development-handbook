---
id: deps/transitive-licenses
domain: deps
locality: global
optin: true
evidence: >-
  The routes below differ from a direct-dependency licence pass only in how
  far down the graph the answer has to hold, not in what produces it. Each of them already
  reports the whole resolved graph rather than the declared direct set, so the
  depth is a property of how the output is read, and a run that answers only
  for direct dependencies has not run this check.
handbook: []
handbook_note: >-
  The handbook's clause already asks to know the third-party surface
  transitively, and deps/licenses covers that baseline; this check is the
  opt-in full-graph depth pass beyond that baseline, not a distinct clause, so
  the handbook states no separate deeper-graph requirement to ground it
  against.
routes:
  - lang: python
    kind: command
    tool: pip-licenses
    argv: [pip-licenses]
    in_env: true
    needs: resolved-tree
    note: >-
      This tool, read for the whole resolved graph rather than for the direct
      set.
  - lang: python
    kind: procedure
    applies_when: >-
      The partition's lockfile pins the transitive set. Where it pins only the
      direct dependencies, there is nothing here to enumerate the transitive
      set from, and that is not a clean result for this partition.
    note: >-
      What answers with no environment installed: the registry procedure
      `deps/licenses` describes answers this check too, and the extra depth
      costs nothing - a complete lockfile already pins the transitive graph, so
      the set to query is the whole of it rather than the direct dependencies.
  - lang: typescript
    kind: command
    tool: npm sbom
    argv: [npm, sbom, "--package-lock-only", "--sbom-format", cyclonedx]
    note: >-
      The npm partition answers this check's depth directly: an npm lockfile pins the transitive graph *and* carries
      each package's `license`, so `npm sbom --package-lock-only` answers on a
      read-only clone - 945 components rather than the 51 the manifest
      declares directly, on the target it was run against.
  - lang: typescript
    kind: command
    tool: pnpm licenses list
    argv: [pnpm, licenses, list]
    needs: resolved-tree
    note: >-
      This tool, read for the whole resolved graph rather than for the direct
      set.
  - lang: typescript
    kind: command
    tool: yarn licenses list
    argv: [yarn, licenses, list]
    needs: resolved-tree
    applies_when: >-
      The partition is on Yarn Classic, as `deps/licenses` states for the same
      route.
    note: >-
      This tool, read for the whole resolved graph rather than for the direct
      set.
  - lang: typescript
    kind: procedure
    tool: "@cyclonedx/cdxgen"
    note: >-
      This tool, read for the whole
      resolved graph rather than for the direct set. What it needs, and the
      environment it needs it in, are that record's and hold here unchanged.
---

# Transitive-license deep dive

Full graph, not just direct - default on for published libraries, ask otherwise.
