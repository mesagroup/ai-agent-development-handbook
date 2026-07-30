# Engineering notes

Practices that were true enough to write down and not universal enough to keep in the engineering handbook (browse its source under `engineering/`; it ships as a standalone HTML artifact rather than as part of this site).

The handbook's value is that its directives are normative and universal, which is what justifies the [traceability matrix](audit/handbook-traceability.md) demanding a row for every section. A practice that is Minor *and* contingent on one execution environment fails that bar: a different but legitimate setup makes it meaningless rather than merely differently-implemented. It is still often true, so it lands here rather than in the bin.

Each entry names the practice, the environment it applies to, and why it is not normative. That last part is the point: this is the cutting-room floor with reasons, so a deleted clause is not re-proposed into the handbook a year later.

This file is deliberately outside `docs/engineering/`. Inside, it would need matrix rows for advisory content and would ride into the standalone handbook artifact as if it carried equal weight.

**Not for obsolete practices.** Contingent goes here; obsolete stays deleted. The rule against passing hash-comments to an agent's Bash tool (removed repo-wide in #549) is not recorded here, because it is not true anywhere any more - it worked around a tool-permission gate that no longer exists.

## Keep the host awake during a long agent run

**Practice.** Before dispatching a long-running sequence of subagents, start a background keep-awake process and kill it when the run completes. On macOS: `caffeinate -i -t <seconds> &`.

**Environment.** A laptop or workstation running the agent harness locally, where the OS suspends the machine on an idle timer and a suspended host kills an in-flight run.

**Why it is not normative.** It is contingent on where the harness runs. A cloud harness, a CI runner, or a server with no idle suspension makes the clause meaningless, and the handbook is not the place to encode one execution environment's power management. The failure it prevents is real but recoverable - you rerun the batch - which puts it at Minor even where it applies. Removed from Part 1 in #552.
