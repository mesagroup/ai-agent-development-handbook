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

**Critical** - a provider reachable from the code, with personal data crossing to it, and absent from the register. That is an unaccounted transfer, and it is the row this check exists to produce.

**Important** - a provider present in both but reached from a path the register does not describe: a second base URL, a fallback endpoint, a gateway in front of the provider the register names. The processor is accounted for and the route is not, so what the register says about region and retention may be true of one path and not of the other.

**Minor** - a registered provider with no reachable call path. That is a stale register entry rather than an unaccounted transfer, so it is not a Critical, and it is worth reporting because it is evidence the register is not being maintained - the same evidence the missing reconciliation date gives `data-protection/processor-register`.

## Tooling fallback

No tool enumerates a project's outbound provider surface, so this is a reading pass over a stated derivation - and the derivation is not stated here. Take the shared outbound-provider surface `SKILL.md` defines and builds once in `audit-core` step 1, rather than re-deriving it, so this row and `data-protection/data-flow-map`'s outbound edges cannot disagree about the one list the domain rests on. Reconciling that union against the register is this check's work; producing it is not.

The surface has a consumer beyond this domain, which is the other reason to take it rather than rebuild it: the planned model and provider supply-chain lens wants the same list for its pinning, end-of-life and region questions, and is meant to consume this derivation rather than derive a second one that is free to disagree with it.

Read the register the same way `data-protection/processor-register` does, and reconcile in both directions: a provider in the surface and not the register is the Critical band, and a provider in the register with no reachable path is the Minor one. Record which source of the derivation produced each provider, because it is what a reader needs to judge the row's confidence - an SDK import is a call path, and a credential name is an inference that a call path exists somewhere.

**The package graph is not the answer, and a clean one is no evidence about this check.** `deps/inventory` enumerates declared packages; a provider reached over plain HTTP never enters the dependency tree at all, and neither does one an agent reaches through a configured tool endpoint. Hand the package question there and do not accept its result as covering this one. `security/sensitive-data` also reads outbound URL construction, but to judge exposure at the call site rather than to enumerate who is called, so its rows answer a different question over the same lines of code.

Where the derivation could not resolve a call path - a base URL assembled at run time, an endpoint read from a database - say so as a limit of the pass rather than reporting the surface as complete.

## Fix

Add the missing providers to the register with the three fields Part 10 asks for, and record the reconciliation date, which is what makes the next pass cheap. Where the surface is large or dynamic, move the outbound calls behind one client layer, so the surface becomes enumerable by construction rather than by search - the same shape `data-protection/boundary-minimization` wants for the redaction step, and the two fixes land in the same place.

## Review lens

**Derivation completeness** - the finding names which of the derivation's four sources produced each provider, so a reader can tell an SDK import from a credential name and judge the confidence of the row accordingly.

**Reachability honesty** - a provider named in code that no configuration reaches is reported as such rather than as an unaccounted transfer, and a dynamic call path the derivation could not resolve is stated as a limit of the pass rather than left implied by a surface presented as complete.

**Single derivation** - the row cites the shared outbound surface rather than a list assembled while writing it, because a second derivation is free to disagree with the first and the disagreement would be invisible in the report.
