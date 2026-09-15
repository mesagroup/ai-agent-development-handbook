---
id: data-protection/provider-surface
domain: data-protection
locality: global
handbook:
  - data-protection/every-processor-needs-an-agreement-and-the-register-must-match-the-code-b
---

# Provider surface against the register

Whether the outbound provider surface derived from the code - SDK imports, configured base URLs, MCP servers and tool endpoints, the credentials the deployment carries - reconciles against the processor register. A provider reachable from the code and missing from the register is the finding, and it is the half of this section a repository can settle on its own.

## Severity

**Critical** - a provider reachable from the code, absent from the register, and with personal data crossing to it *established by an artifact* rather than assumed: the data-flow map's edge, the operator's declaration at scope time, or a call site plainly handing over user content. That is an unaccounted transfer, and it is the row this check exists to produce.

**Important** - the same provider, reachable and unregistered, where nothing documents what crosses to it. An unregistered provider whose payload is undocumented is a true finding and a fixable one; the same row called Critical asserts a transfer of personal data on the strength of a base URL, which is what `SKILL.md` withdraws rather than downgrades. An error tracker's endpoint or a geocoding service in an environment template is exactly this case.

The two bands below are **mechanism** bands and stand whatever established the surface: a provider the register already names is a provider the target itself has declared a processor, and each band cites a route or an entry in a document rather than a payload.

**Important** - a provider present in both but reached from a path the register does not describe: a second base URL, a fallback endpoint, a gateway in front of the provider the register names. The processor is accounted for and the route is not, so what the register says about region and retention may be true of one path and not of the other.

**Minor** - a registered provider with no reachable call path. That is evidence the register is not being maintained, which is evidence the register is stale rather than evidence of an unaccounted transfer, and it is not an unaccounted transfer, so it is not a Critical. **Report it as an entry to confirm and re-date, never as one to remove.** A provider the derivation could not reach is indistinguishable here from one that is genuinely no longer called - and the providers the derivation misses are precisely the ones whose call path it could not resolve, the case this record already tells you to declare as a limit. The register's owner decides; an audit that talks a team into deleting the entry has removed a processor from the document that exists to account for it.

## Tooling fallback

No tool enumerates a project's outbound provider surface, so this is a reading pass over a stated derivation - and the derivation is not stated here. Take the derived personal-data surface `SKILL.md` defines and builds once in `audit-core` step 1, and read its outbound-edge axis, which is this check's subject, rather than re-deriving it - so this row rests on the one list the domain builds rather than on a second derivation. Reconciling that union against the register is this check's work; producing it is not.

The surface has a consumer beyond this domain, which is the other reason to take it rather than rebuild it: the planned model and provider supply-chain lens wants the same list for its pinning, end-of-life and region questions, and is meant to consume this derivation rather than derive a second one that is free to disagree with it.

Read the register for the three fields it carries, and reconcile in both directions: a provider in the surface and not the register is the Critical band, and a provider in the register with no reachable path is the Minor one. Record which source of the derivation produced each provider, because it is what a reader needs to judge the row's confidence - an SDK import is a call path, and a credential name is an inference that a call path exists somewhere.

**The package graph is not the answer, and a clean one is no evidence about this check.** `deps/inventory` enumerates declared packages; a provider reached over plain HTTP never enters the dependency tree at all, and neither does one an agent reaches through a configured tool endpoint. Hand the package question there and do not accept its result as covering this one. `security/sensitive-data` judges exposure at the call site rather than enumerating who is called, so its rows answer a different question. **Do not restate its findings here and do not treat its rows as covering this check either** - a call site it cleared for exposure is still an unregistered provider if the register does not name it. `security/agent-privilege-surface` asks what one agent is allowed to reach rather than which processors the deployment calls, so a grant it judges narrow enough is still an unregistered provider if the register does not name it. Hand a grant that looks over-broad there rather than widening this check to judge it.

Where the derivation could not resolve a call path - a base URL assembled at run time, an endpoint read from a database - say so as a limit of the pass rather than reporting the surface as complete.

## Fix

Add the missing providers to the register with the three fields it carries - a signed data processing agreement, the provider's training position and, where its default is to train, the mechanism opted out by, and the retention window including any longer abuse-monitoring one - then record the reconciliation date, which is what makes the next pass cheap. The fields are named here rather than cited, because the plugin ships only `.agents/skills/` and an agent running this check from a plugin cache in another repository cannot open the handbook to look them up. Where the surface is large or dynamic, move the outbound calls behind one client layer, so the surface becomes enumerable by construction rather than by search.

## Review lens

**Derivation completeness** - the finding names which source of the derivation produced each provider, so a reader can tell an SDK import from a credential name and judge the confidence of the row accordingly.

**Reachability honesty** - a provider named in code that no configuration reaches is reported as such rather than as an unaccounted transfer, and a dynamic call path the derivation could not resolve is stated as a limit of the pass rather than left implied by a surface presented as complete.

**Single derivation** - the row cites the derived personal-data surface rather than a list assembled while writing it, because a second derivation is free to disagree with the first and the disagreement would be invisible in the report.
