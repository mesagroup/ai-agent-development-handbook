---
id: deps/model-catalog-indirection
domain: deps
locality: global
handbook:
  - agent-harness/resolve-models-through-aliases-never-hard-coded-ids
evidence: >-
  Two lists and the relation between them: every site on the application
  path that names a provider model, with the `file:line` and the literal as
  written, and every catalog the project resolves an alias through, with the
  `file:line` of its table. The verdict is read off the relation - each
  naming site either goes through a catalog or does not - so a row records
  the site, the catalog entry it resolves through where there is one, and
  the word `inline` where there is none. A project with no catalog and one
  inline site records that site under the clean value, because the reader
  has to see what was counted to trust a clean result over an absence.
routes:
  - lang: any
    kind: procedure
    disposition: runs
    note: >-
      **Find the catalogs first, then the naming sites, then relate them.** A
      catalog is a project-owned table that maps a short alias to a
      provider's model identifier and is read at runtime: a settings module
      holding the mapping, a YAML or JSON table, a router or gateway
      configuration that keys model names by alias, a factory that takes an
      alias and returns a client. Record its `file:line` and whether the
      alias prefix encodes the provider. A settings value that *is* the raw
      provider identifier is not a catalog, however central: it holds no
      alias and contains no churn, so it counts as a naming site. Then
      collect every site on the application path that names a provider
      model - a literal identifier in the argument that constructs an SDK
      client, an agent or prompt definition, a deployment manifest, an
      environment template's default value - and for each, follow the name
      back. A call that passes on a name it received names nothing and is
      not a site; that is the sibling's rule too, so the two records
      enumerate the same homes. For each site: an
      alias resolved through a catalog is the claim being met, a provider
      identifier written where it is used is the claim being missed. Where
      `deps/model-pinning-and-eol` has already collected those sites in this
      run, start from its list rather than building a second free to
      disagree with it, and where it has not, collect them here from the same
      homes and say in the report that this record derived them. Take from
      that list only the application-path model identifiers: it also carries
      provider API versions, which name no model and never count as a naming
      site, and the eval-side identifiers the sibling gathered as comparison
      evidence, which this record reads once, below, and never counts toward
      the application-path total. Drop its catalog-entry rows too: where the
      sibling followed an alias into a catalog it recorded the identifier the
      catalog resolves to with the catalog's own `file:line`, and a row whose
      `file:line` lies inside a catalog is that catalog's entry, found in
      the first step above, never an inline site. Read unfiltered, a project
      whose every call goes through its catalog would count each catalog
      row as a bypass and take the Important band for having done exactly
      what the clause asks. A project with one production model, one API
      version and one eval pin has one naming site, not three. **What
      this reads is the path to the name, not the name**: whether the
      identifier at the end of it is pinned or sunset is
      `deps/model-pinning-and-eol`'s question, run over the same sites, and
      this record takes none of it back. Count the inline sites and read the
      verdict from the count and the catalogs together, using the definitions
      in the body below rather than judging the project's size. Then read the
      eval side's naming sites, once: from the sibling's comparison list
      where this run already holds it, and otherwise collected here from
      the eval configs, runners and screening scripts, the same homes the
      sibling reads, because each global check runs as its own agent and
      this one cannot assume the sibling went first. Report an eval config
      that names a
      provider model directly while a catalog exists as its own line, because
      pointing one agent at a dozen candidates by varying an alias is the case
      the handbook clause names, and an eval that bypasses the catalog is the
      case where that stops being a one-token change.
---

# Models resolved through a catalog, never named inline

Does the application reach its provider models through a short alias resolved in one central catalog, or does it name concrete provider identifiers where they are used? The handbook asks that switching the model a run uses be a one-token change and that screening a dozen candidates never touch the agent, and both hold only where the real identifier lives in one place. An identifier written at the call site is a decision copied into every file that calls a model, and a provider's churn then reaches every one of them.

**This record reads the path to the identifier, and its sibling reads the identifier.** `deps/model-pinning-and-eol` collects the same naming sites and asks whether each model is pinned where the provider allows it and still supported; a concrete, pinned, current identifier written inline satisfies that check completely and is exactly what this claim forbids, which is why the two are separate records over one surface rather than one record with two verdicts. `eval/reproducibility` owns whether an eval run recorded the model that produced its numbers, and `security/secrets-in-code` owns the credential the catalog would also centralize; this record names neither of those questions as its own and hands a finding of that shape to the check that owns it.

**Three states, defined here so an agent reads them rather than infers them.** A catalog exists and every application-path site resolves through it: the clean value, with the catalog's `file:line` recorded. No catalog exists and exactly one site names exactly one provider model: **also the clean value**, with that site recorded as the evidence, because the claim's benefit is that switching model becomes a one-token change and at a single site it already is one; asking a project with one call to build an indirection layer asks for structure that contains nothing. Every other shape is a finding: more than one inline site with no catalog, or any inline site while a catalog exists. The single-site clean value is a definition rather than a threshold an agent sets, and the site is recorded precisely so that a reader who disagrees with the definition can see what it covered.

**The clean value here is not `not-applicable`**, which `audit-core` reserves for a check with no lens in a partition's languages: this check reads declarations, has a lens everywhere, and a project that names no model at all is one that ran and found nothing - with the homes searched recorded beside it, and with the provider-configured-but-no-model case handed to `deps/model-pinning-and-eol`, which owns the unpinned default. Either absence is a claim about the whole surface rather than the first place looked in: a model may be named in a config module, an agent definition, a deployment manifest or an environment template, and finding none in the first of those settles nothing.

**What makes a catalog the single place.** One table, one file, one resolution function, read by every site that needs a model; an alias whose prefix says which provider serves it, so the call site never knows. Two catalogs are two places provider churn reaches, and an alias with no provider prefix makes the call site guess or the catalog carry a second mapping. Neither undoes the indirection, so both are Minor, and both are recorded so the fix is one move rather than a discovery.

## Severity

**Important** - a provider model is named inline at more than one site on the application path and no catalog exists. Switching model is a code change at every site, and the sites can already disagree.

**Important** - a catalog exists and a site on the application path names a provider model directly, bypassing it. The indirection is built and one call has stepped around it, so the catalog no longer knows every model the product runs.

**Minor** - an eval configuration names a provider model directly while the application resolves its own through a catalog. Screening candidates is the case the clause exists for, and this is where it has stopped being a flag change.

**Minor** - more than one catalog, or a catalog whose aliases do not encode the provider. The indirection holds; its containment does not.

## Fix

**Introduce one catalog and route every naming site through it**, taking the alias names from what the sites already call the models where a name exists, and putting the provider in the alias's prefix. The identifiers move; nothing about which model runs changes, so the sites that moved are the whole diff and a reader can check that the resolved identifier at each is the one that was there.

**For a site bypassing an existing catalog**, add the alias to the catalog and replace the literal, and read why the site bypassed it: a model the catalog did not carry is an entry to add, and a deliberate override is a suppression to record with its reason so the next audit reads a decision rather than a leak.

**Where the clean value rested on a single inline site**, no fix is asked; record the site, and the next model added to the project is the moment the catalog is built.

## Review lens

**Path over name** - does the report say how each identifier was reached, or only what it is? (Highest-value catch: a project whose every model is pinned and current, reported clean by the sibling, with the identifiers copied into six call sites.)

**Catalog reality** - is the thing called a catalog a table of aliases, or a settings value holding one raw identifier? The second centralizes the literal and none of the churn, and a report that credits it with the indirection has read the file's name rather than its contents.
