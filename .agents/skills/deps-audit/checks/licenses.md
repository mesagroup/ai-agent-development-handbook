---
id: deps/licenses
domain: deps
locality: global
handbook:
  - security-supply-chain/depend-only-on-what-you-can-account-for-a
tooling:
  python: [pip-licenses]
  typescript: [license-checker]
---

# License compatibility

Each dependency's license vs the project's license/policy: copyleft (GPL/AGPL/LGPL) pulled into a permissive project, "unknown"/missing license metadata, non-OSI or source-available licenses, license *changes* across a version bump.

## Severity

**Critical** - a disallowed/incompatible license in a dependency that is actually shipped/distributed; a dependency with no resolvable license in a published library.

**Important** - copyleft in a distributed artifact pending legal review.

## Tooling fallback

**Python** - `pip-licenses` (with `--format` for SPDX-ish output), or read each installed dist's `*.dist-info/METADATA` (`License` + `Classifier: License ::`). Map to SPDX ids; flag `UNKNOWN`.

## Fix

Replace or remove a disallowed-license dependency; update imports; re-test.

## Review lens

Is each verdict right for the project's own license and distribution model? (copyleft nuance, LGPL dynamic-linking, dual licenses)

Direct vs transitive attribution is right; a transitive-only finding isn't pinned as if it were direct.
