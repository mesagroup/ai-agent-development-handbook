---
id: security/agent-privilege-surface
domain: security
locality: global
handbook:
  - security-supply-chain/grant-the-agent-the-least-privilege-it-needs
---

# Agent privilege surface

What is each agent in this project *allowed to do*, and does any one of them hold private-data access, untrusted-content exposure and the ability to act on the outside world at once with no human gate on the acting edge? The code checks in this domain read what the code does with input it receives; this one reads what the deployment lets an agent reach before any of that code runs. A diagnostic, research or analysis agent holding a write grant is the same claim's other half.

## Severity

**Critical** - one agent holds all three powers with no human gate on the acting edge. This is the lethal trifecta: a prompt injection carried in the untrusted content can read the private data and ship it out, with no further foothold required.

**Important** - an agent whose role is diagnostic, research or analysis holds a write grant; a grant widened wholesale rather than per tool; production or pipeline write access held for convenience.

**Important** - the grants and the agents cannot be paired: agents are declared but their grants are inherited entirely from a runtime default, or a grant is declared - an MCP server, an auto-approval setting, an agent-scoped credential - with no agent definition saying who holds it. A surface nobody wrote down as some agent's cannot have the trifecta ruled out, and the clause asks for these powers to be reasoned about explicitly.

## Tooling fallback

Needs reading - no scanner in this domain's evidence pass reaches this: read what the project declares an agent may do, wherever it declares it. The property that makes something part of that surface is that it *widens or gates what an agent can reach at run time*, and the common homes are an agent definition carrying an explicit tool list, an MCP server declaration, a permission or auto-approval setting, and the credentials the agent's environment carries. Read every home the project uses rather than the first one found: each catches grants the others do not mention, and an MCP server appears in no import.

**Classify each granted tool onto three axes** - does it reach private data, does it ingest untrusted content, does it act on the outside world (write, spend, or send). The classification is a reading of what the tool reaches in *this* deployment, not a property of its name: a file-read tool over a repository holding customer records is private-data access, a web fetch or an inbox reader is untrusted content, and a shell, an HTTP write or a payment call is an acting edge. A tool can sit on more than one axis, and one that sits on none still belongs in the report as read.

**The evidence pointer names the agent, the declaring `file:line`, and the granting tool on each axis it occupies.** All three, because a trifecta finding is unreadable without them: a reader who cannot see which grant supplied which axis cannot tell whether narrowing one of them closes the finding.

**A project declaring no privilege surface at all gets this domain's clean value, with what was read recorded beside it** - the homes searched and the absence found. What has to be empty is the whole surface rather than the first home looked in: a project with no agent definition file but an MCP server declaration, an auto-approval setting or an agent-scoped credential has grants to classify, and a grant no agent definition claims is the `Important` finding above rather than an absence. Where every home is empty there is nothing to constrain, so the claim is satisfied vacuously, and that is a result rather than a missing one. It is deliberately not `not-applicable` - see `audit-core` for what that status is for - because the lens here applies fine to a project that simply has no agents. Reporting it as `not-applicable` would put an unanswered-looking row where an answered one belongs.

**The three neighbours, and what each keeps.** `ci/permissions-secrets` owns the pipeline token's own least privilege, which is the pipeline's power rather than an agent's. `data-protection/provider-surface` asks whether every outbound provider is in the processor register. This check reads agent and MCP declarations for a different question, and asking two questions of one artifact is not double counting, which is why this record names it. The prompt domain owns what an agent is *told*; this check owns what it is *allowed to do*. The handbook clause draws a different line again, pairing *allowed to do* against what a model or tool *returns*, which is the code checks' half of this domain.

**This check reports the configuration it finds and does not rate the architecture.** Which agents a project has, and whether a capability should exist at all, are not its question - only whether the three powers are concentrated without a gate, and whether a read-only role was widened.

## Fix

**Split the trifecta or gate the acting edge.** Narrowing is the first move - take the agent down to the axes its task needs, per tool and per purpose rather than wholesale - and where a task genuinely needs more than one of the three at once, put a human approval on the acting edge instead. Returning a diagnostic agent to read-only tool and MCP access is the same fix in its simplest form.

**What closes it is a read of the changed configuration, not the domain's default gate.** The scanner and the test suite cannot see a narrowed tool list or an added approval hook, so neither a clean SAST run nor a green suite is evidence that this finding was fixed. Re-read the declaration and confirm which axis the agent no longer holds, or which edge now has a gate.

## Review lens

**Grant narrowing, not grant renaming** - after the fix, does the agent actually hold fewer of the three axes, or has the same reach been re-expressed? (Highest-value catch: a tool removed from a list while an MCP server or an inherited credential still supplies the same axis, which reads as a narrowed grant and is not one.)
