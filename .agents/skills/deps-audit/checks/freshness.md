---
id: deps/freshness
domain: deps
locality: global
evidence: >-
  What the check compares per package is the pin, or the version actually
  installed, against the latest release, plus whether the pinned release is
  yanked; an unpinned direct dependency is what the lockfile scan reports
  rather than a comparison against anything. On a workspace the coverage of
  that comparison is part of the evidence: an answer covering the root
  manifest alone says nothing about the manifests it never looked at, and
  that is per-command rather than per-manager - `pnpm audit` and
  `pnpm licenses list` are both recursive by default on the same tree - so
  check each command you run rather than assuming the manager's default.
handbook:
  - security-supply-chain/depend-only-on-what-you-can-account-for-a
routes:
  - lang: python
    kind: command
    tool: uv
    argv: [uv, pip, list, "--outdated", "--python"]
    in_env: true
    needs: resolved-tree
    note: >-
      Reads the installed environment rather than the lockfile, so it needs
      the tree resolved.

      The argv ends at a bare `--python` and is not a complete invocation.
      Name the interpreter explicitly on this route, as `uv pip list
      --outdated --python <path-to-venv-python>`; the path is the caller's
      to resolve, which is why the argv stops where the placeholder starts.
    alone_insufficient: >-
      An outdated list answers the outdated half of this check alone:
      whether a direct dependency is unpinned, and whether a pinned release
      is yanked, are the lockfile scan and the registry comparison the
      procedure route below carries, so a clean list beside an unread
      lockfile is not this check answered.
  - lang: python
    kind: command
    tool: uv
    argv: [uv, pip, list, "--outdated"]
    disposition: superseded
    in_env: true
    needs: resolved-tree
    note: >-
      The unqualified form, superseded by the one above rather than offered
      beside it: without `--python <path>`, `uv pip list --outdated` can
      return empty output at exit 0 against a tree with stale packages in it,
      rather than erroring or falling back to a discovered venv, so a clean
      run of the unqualified command is not evidence that nothing is outdated
      - it can equally be evidence the command never found the environment.
  - lang: python
    kind: command
    tool: pip
    argv: [pip, list, "--outdated"]
    in_env: true
    needs: resolved-tree
    note: >-
      `pip list --outdated` reads the installed environment rather than the
      lockfile, so it needs the tree resolved. It needs no interpreter flag;
      it introspects whichever interpreter it is running under rather than
      depending on venv-discovery logic.
    alone_insufficient: >-
      An outdated list answers the outdated half of this check alone. Whether
      a direct dependency is unpinned, and whether a pinned release is yanked,
      are the lockfile scan and the registry comparison the procedure route
      below carries, so a clean list beside an unread lockfile is not this
      check answered.
  - lang: python
    kind: procedure
    note: >-
      What answers with no resolved tree at all, so a withheld grant leaves
      this check answerable on a Python partition: the lockfile scan for
      floating direct pins, and the per-package registry comparison, which
      answers outdated-ness and yanked-ness from the pins already in the
      clone. Read `uv.lock`, `poetry.lock` or the pip-compile output for the
      direct and transitive pins, then ask the registry per package:
      `https://pypi.org/pypi/<name>/json` reports the latest release in
      `info.version`, which is the comparison the tiered routes above would
      have made, and `https://pypi.org/pypi/<name>/<version>/json` reports
      `yanked` for the pinned release. Take the latest release from the
      project endpoint rather than the per-version one, which describes only
      the version asked for and cannot tell you something newer exists. That
      path needs network rather than the tree, so it survives a withheld
      grant and fails instead where the audit has no network, which is
      `no-evidence (tool-unavailable)` rather than `not-permitted`. What the
      resolved tree adds is the versions actually installed, which can differ
      from the pins; on a foreign repository the pins are the more faithful
      subject anyway.
  - lang: typescript
    kind: command
    tool: npm outdated
    argv: [npm, outdated]
    needs: resolved-tree
    note: >-
      The package manager's own subcommand, preferred once the tree exists
      and never a fallback for the untreed case: it reads *installed* state,
      not the lockfile that happens to be present. `npm outdated` on a tree
      with no `node_modules` reports every production dependency as
      `MISSING`, and its own source drops any non-production dependency that
      is missing from the output entirely, so devDependencies vanish rather
      than being reported as outdated.
    alone_insufficient: >-
      An outdated list answers the outdated half of this check alone. Whether
      a direct dependency is unpinned, and whether a pinned release is yanked,
      are the lockfile scan and the registry comparison the procedure route
      below carries, so a clean list beside an unread lockfile is not this
      check answered.
  - lang: typescript
    kind: command
    tool: pnpm outdated
    argv: [pnpm, outdated, "-r"]
    needs: resolved-tree
    note: >-
      The package manager's own subcommand, preferred once the tree exists
      and never a fallback for the untreed case: `pnpm outdated` hard-errors
      with no lockfile at all, and with a lockfile but no install it reports
      every dependency as outdated because the installed version is
      undefined. **On a workspace, ask for the workspace**, which is why the
      argv carries `-r`: bare `pnpm outdated` reports the root manifest only.
      On a 9-manifest pnpm workspace declaring 254 dependencies, of which 10
      sit at the root, it returned 10 entries and `pnpm outdated -r` returned
      136, and on the seeded pnpm fixture it listed the one outdated pin
      declared at the root and missed the three declared in its members.
      Nothing in the bare output says the other manifests were never looked
      at. One output caveat:
      `pnpm outdated --json` writes registry warnings to stdout ahead of the
      JSON, so a run that pipes it straight into a parser fails on output the
      command considers successful.
    alone_insufficient: >-
      An outdated list answers the outdated half of this check alone. Whether
      a direct dependency is unpinned, and whether a pinned release is yanked,
      are the lockfile scan and the registry comparison the procedure route
      below carries, so a clean list beside an unread lockfile is not this
      check answered.
  - lang: typescript
    kind: procedure
    tool: npm-check-updates
    note: >-
      The default where the audit has not been granted a tree, and the
      default for a Yarn Berry partition whatever the grant: a registry
      package a one-shot runner can fetch, which selects the ecosystem with
      `--packageManager` and reads `package.json` against the registry rather
      than any installed state, so it is the option that answers on a
      read-only clone. Yarn Berry dropped `yarn outdated` and offers only the
      interactive `yarn upgrade-interactive`, which an unattended audit
      cannot drive; on Yarn Classic `yarn outdated` is the manager's own
      subcommand and takes the same preference the npm and pnpm routes above
      carry once the tree exists. `npm-check-updates` reads the root manifest
      the same way `pnpm outdated` does. The record names the tool and the
      flag that selects the ecosystem and prescribes no command line, so
      there is no argv to declare and a `kind: command` route would have to
      invent one.
  - lang: typescript
    kind: procedure
    note: >-
      What answers with no tree: read the partition's *own* lockfile for
      floating direct pins, whichever of `package-lock.json`,
      `pnpm-lock.yaml`, `yarn.lock` or `bun.lock` that is; check the registry
      for deprecated/yanked releases.
---

# Freshness

Outdated (a newer release exists), yanked, or EOL versions; unpinned/floating direct dependencies (reproducibility + drift risk).

## Severity

**Important** - an unpinned *direct* runtime dependency; a yanked resolved version.

**Minor** - outdated-but-safe versions.

## Fix

Bump/pin to a fixed version; regenerate the lock (`uv lock` / equivalent) and re-run tests.

## Review lens

**Dependency attribution** - direct vs transitive attribution is right; a transitive-only finding isn't pinned as if it were direct.
