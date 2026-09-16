---
id: deps/model-pinning-and-eol
domain: deps
locality: global
handbook:
  - security-supply-chain/depend-only-on-what-you-can-account-for-b
evidence: >-
  The evidence is where the model is named, not every call that passes the
  name along: the model identifier and API version as the application
  configures them - a settings value, an environment template, a deployment
  manifest, the argument that constructs an SDK client, or a prompt or agent
  definition - with the `file:line` of each, and beside it two facts that
  live at the provider rather than in the target: whether the provider
  publishes a pinnable form of that identifier, and its end-of-life date.
  A run that cannot reach the provider has the declarations and neither
  provider fact, and **both halves then report `no-evidence` with that as
  the reason**. Neither collapses to `ok`: a pin that was never looked up is
  not a pin known to be absent, and a sunset that was never looked up is not
  a sunset known not to exist.
routes:
  - lang: any
    kind: procedure
    disposition: runs
    note: >-
      **The pin, read from the project's own configuration.** Collect every
      model identifier and provider API version the application declares:
      settings and config modules,
      environment templates such as `.env.example`, deployment manifests,
      the arguments to SDK client construction, and any prompt or agent
      definition that names a model. For each, ask whether the provider
      publishes a pinnable form and whether the project uses it. **Collect
      the eval-side identifiers too, as comparison evidence rather than as
      findings**: the review lens below turns on whether the evals pin a
      version the production path does not, and that comparison has no
      evidence if only one side was read. The finding stays on the
      application path, because that is the model the product answers with;
      `eval/reproducibility` owns whether the eval recorded its own.
      **Where the
      provider cannot be reached, `no-evidence` covers exactly the question
      the provider would have answered** - whether a pinnable form exists,
      which is the whole difference between the `ok` below and the Important
      band - **and nothing else**. Everything decidable from the declarations
      already in the clone still reports: a provider configured with no model
      named, and two declaration sites that disagree about which model runs.
      Neither needed the network to begin with, and folding them into one
      `no-evidence` suppresses a finding nothing was missing to make. Record
      the identifiers found either way, because that half of the evidence
      stands and the next run starts from it. An alias
      that resolves to whatever the *provider* currently points it at is the
      unpinned case, and it is unpinned however stable it has been so far.
      **A project's own alias is not that.** The handbook asks for a short
      internal name resolved through a central catalog, and that pattern is
      what it recommends rather than what this check flags: follow the alias
      into the catalog and read the identifier the catalog resolves it to.
      The finding is a provider-side moving pointer wherever it is finally
      named, which on a project that has a catalog means inside the catalog,
      and on one that has none means at every site that names a model.
      Record the `file:line` of each declaration, and the identifier as
      written.
  - lang: any
    kind: procedure
    disposition: runs
    note: >-
      **The lifetime, which the repository does not contain.** Compare each
      identifier collected above against the provider's own published
      deprecation or end-of-life schedule. That schedule lives at the
      provider and nowhere in the target, so this half needs the network the
      way `deps/transitive-licenses` needs the registry, and a run without
      it reports `no-evidence` on the lifetime with that as the reason. It
      never reports `ok`: a model whose sunset date was not looked up is not
      a model known to have none, and the two read identically in a report
      that conflates them.
---

# Model pinning and model or endpoint end-of-life

Does the project pin the model versions it depends on where the provider allows pinning, and is any model or endpoint it names approaching or past its end of life? A silent model upgrade is an unpinned dependency: behaviour moves, eval numbers move with it, and nothing in the diff records that anything changed. A sunset model or API version is a dependency with a known break date that the project has not read.

**This is the package graph's own failure modes on the AI surface**, which is why the check lives here rather than in a lens of its own. `deps/freshness` asks the same two questions of a registry package - is the pin floating, is the release still current - and this record asks them of a model identifier. The difference is only where the answer lives: a registry serves the package's metadata, and a provider serves the model's.

**What this check does not read, because a sibling already does.** `eval/reproducibility` owns the pin on the eval surface: whether a run recorded the model version that produced its numbers. `data-protection/provider-surface` owns the inventory: which providers the project depends on at all, derived from SDK imports, configured base URLs, MCP and tool endpoints and credential names. `data-protection/residency-pinning` owns the region. This record takes none of those back; it reads the application's own configuration for a version and a lifetime, and where a provider list has already been derived - the shared surface a data-protection run builds once, which `data-protection/provider-surface` reconciles against the register - it consumes that rather than building a second free to disagree with it.

**That shared surface is often absent, and this check still runs.** It is built inside a data-protection run, so a direct `deps-audit` invocation never has it, and a sweep whose operator answered that the target processes no personal data has removed that domain from scope entirely while this check is not opt-in and runs anyway. In that case derive the provider list here, from the same homes the pin is read from, and say in the report that it was derived rather than consumed. Reporting `no-evidence` because a sibling domain did not run would make a check about model versions depend on a question about personal data, which is not a relationship either claim has.

**Two absences look alike and are opposites, so separate them before reporting either.** A project that configures **no model provider at all** - no SDK client, no base URL, no model credential - gets this domain's clean value, with what was read recorded beside it: the homes searched and the absence found. A project that **configures a provider and names no model** is not empty at all: it is running the provider's default, which is the least pinned state there is, and it reports the unpinned finding rather than a clean value. Find the providers first and the identifiers second, because only the first of those tells you which kind of absence you are looking at.

The clean value here is not `not-applicable`, which `audit-core` reserves for a check with no lens in a partition's languages: this check reads declarations, has a lens everywhere, and a genuinely empty surface is it running and finding nothing. Either absence is a claim about the whole surface rather than the first place looked in: a project may name its model in a config module, a deployment manifest, an environment template or an agent definition, and finding none in the first of those settles nothing.

**`ok` where the provider publishes no pinnable form**, with that fact recorded and with the provider actually consulted. A project cannot pin what the provider does not version, and reporting it as a finding asks for a fix that does not exist. What is recorded is the absence, so the next audit does not re-derive it.

**The two routes are one procedure in two halves, run in the order they appear**, because the second reads the identifiers the first collected. They report separately: a pin finding and a lifetime finding are different findings with different fixes, and a run that answered the first and not the second says so rather than letting one status stand for both. Neither is a tool, because no scanner in this domain reads a model identifier - the pin lives in the project's configuration and the lifetime lives at the provider - so the routes carry the whole prescription.

## Severity

**Critical** - a model or API version the project depends on is past the provider's announced end-of-life date. The break is scheduled and the date has passed.

**Important** - a model identifier is unpinned where the provider publishes a pinnable form. This is the silent-upgrade case, and it is the one the handbook clause names.

**Important** - a provider is configured and no model is named anywhere on the application path, so the provider's own default answers. This is the strongest form of the band above rather than an absence: the project has not merely failed to pin a version, it has not recorded which model it runs, and a report that reads the missing declaration as an empty surface hands back a clean result for the case this check most exists to catch.

**Important** - a model or API version is approaching its announced end of life. Report the date rather than a distance, because a distance read from a report is stale the day after it is written.

**Minor** - the project pins its models but records the pin in one place and uses an alias in another, so the two disagree and whichever loads last wins.

## Fix

**Pin the identifier to the provider's versioned form** wherever one exists, in the application's configuration rather than at the call site, so one place decides it. Where the project deliberately tracks a moving alias, record that decision beside the declaration with its reason, which turns a finding into a suppression the next audit can read.

**For a model at or approaching end of life, the fix is the migration, and the check's own close is the date.** Replacing the identifier closes it; noting the sunset does not. Where the migration is scheduled rather than done, the suppression records the target date and the replacement, so an audit after the sunset reads a broken promise rather than a clean result.

**Where the lifetime could not be established**, the fix is to establish it once and record it beside the declaration, because a project that cannot say when its model sunsets will not notice the day it does.

**Every fix here changes which model runs, so it needs a behavioural re-check rather than the domain's default gate.** Pinning a floating alias, or migrating off a sunset model, moves the model the product answers with; the lockfile still resolves and the unit tests still pass, because neither reads a model identifier. Re-run the project's evals or its smoke gate against the new pin before the fix is trusted, and qualify that as the project's own harness rather than this audit's - `eval-audit` owns whether that harness measures anything, and a green run on an instrument it would fail is not evidence.

## Review lens

**Pin locality** - is the pin in the application's configuration, or only in the eval's? (Highest-value catch: a project whose evals pin a version and whose production path takes the provider's default, so the numbers were measured on a model the product does not run.)

**Lifetime honesty** - where the report says a model is current, was the provider's schedule actually read, or was the absence of a known sunset treated as the absence of a sunset? The two produce the same word and different guarantees.
