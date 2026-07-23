---
name: prompt-audit
description: "Audit the static authoring quality of a project's system prompts and Agent SOPs: conformance to the SOP specification (Overview/Parameters/Steps structure, .sop.md naming, snake_case params), constraint hygiene (RFC 2119 usage, negative constraints carrying their reason), clarity and internal consistency, cognitive load / directive density, and redundancy. Use before relying on a prompt or SOP, after writing or heavily editing one, when a prompt has grown into an overloaded wall of rules, or when the user asks to audit / review / lint a prompt or SOP for how well it is written. Works on any project with prompts or .sop.md files. Runs on the audit-core engine. Behavioral, model-level prompt quality (drift-vs-tools, injection-resistance, is-it-evaluated) belongs to eval-audit; prompt-injection as application security belongs to security-audit — this skill owns how well the prompt is *written*."
---

# Prompt Audit (system prompts & Agent SOPs)

A domain specialization of **[audit-core](../audit-core/SKILL.md)** — read that first; it owns the loop (scope → parallel evidence → findings matrix → plan → subagent-driven fixes → review → PR) and the cross-cutting rules. This skill supplies the **static authoring-quality** lens for prompts and SOPs.

The split from its closest sibling is deliberate and mirrors `test-audit` vs `eval-audit`: **`eval-audit`** owns *behavioral, model-level* prompt quality (does the prompt hold under adversarial input, has it drifted from the current tools/code, is the behavior actually measured); **this skill** owns *how well the prompt is written on the page* (is it well-formed, clear, consistent, and not overloaded). The two cross-link rather than overlap: a prompt can be immaculately structured and still behave badly, and vice versa, so a real prompt change usually wants both passes.

**Core principle:** a prompt is source code for a model, and the same things that make source unmaintainable make a prompt unreliable. A contradiction the model silently resolves the wrong way, a negative rule with no reason it quietly reintroduces, a section so dense it drops half its constraints — these are defects you can see *on the page*, before a single token is generated, and they are cheaper to catch there. A well-written prompt is not decoration: it is the difference between a directive the model follows every run and one it follows when the context happens to be short enough.

**Announce:** "I'm using the prompt-audit skill (on the audit-core engine) to audit the prompts and SOPs."

**Bash rule:** never pass a line starting with `#` to the Bash tool (you or any subagent) — hash comments confuse the tool-permission subsystem.

## When to use

- Before trusting a new or heavily edited prompt / SOP that drives real agent behavior.
- After a prompt has accreted rules over many changes and is now a wall of MUSTs nobody can hold in their head.
- When onboarding an SOP written elsewhere, to check it conforms to the project's SOP format.
- When the user asks to audit, review, or "lint" a prompt or SOP for quality, clarity, or complexity.

**Not for:** *behavioral* prompt quality — whether the prompt is evaluated, drifts from the tools, or resists injection (use `eval-audit`); prompt-injection as an *application-security* exposure (use `security-audit`); a one-off "make this prompt read better" edit with no audit trail (just edit it). This skill owns the static, on-the-page authoring quality; it cross-links the others rather than covering them.

## 1. Subject & scope

The project's prompt and SOP assets:

- **Agent SOPs** — `.sop.md` files (the structured, reusable prompts specified by the [`agent-sop`](https://github.com/strands-agents/agent-sop) format).
- **System prompts & tool descriptions** — the prompt `.md` files (and Jinja2 `.j2` prompt templates) that configure agents, sub-agents, and tools. For `.j2` templates, render every variant first and audit each rendered version, since a template can read fine and render broken.

Detect where these live (in this repo: `.sop.md` files anywhere, plus the `**/prompts/` directories). Establish which prompts are **load-bearing** (drive a production agent or a sub-agent) versus throwaway (a one-off eval prompt), so severity can weight the former.

Slice the parallel evidence pass **one read-only agent per prompt/SOP file** (or per small group of related prompts) — each file audits cleanly in isolation, and cross-file concerns (a shared rule that drifted between two prompts) surface when the findings are consolidated.

## 2. Dimensions (findings-matrix columns)

- **SOP-spec conformance** (for `.sop.md` files) — required sections present and in order (**Overview**, **Parameters**, **Steps**); each step carries a **Constraints** block; optional **Examples** / **Troubleshooting** used where they'd help. Correct `.sop.md` extension and kebab-case filename; `snake_case` parameter names, each marked `(required)` / `(optional[, default: …])`, with required listed before optional. (Non-SOP prompts skip this column; they are judged on the rest.)
- **Constraint hygiene** — directives use RFC 2119 keywords (**MUST** / **SHOULD** / **MAY** and negatives) so the requirement level is unambiguous, not a vague "try to" / "please"; every **negative** constraint (MUST NOT / SHOULD NOT / NEVER) states its **reason inline** ("don't do X *because Y*"), which is what stops a model quietly reintroducing X; requirement levels are used consistently (not a MUST that's really a preference, nor a SHOULD guarding something catastrophic).
- **Clarity & internal consistency** — no two instructions contradict each other; no dead instruction (references a step, tool, or artifact that no longer exists); no ambiguous directive that can be read two ways; each instruction says *what to do* and, where non-obvious, *why*.
- **Cognitive load & density** — no section overloaded past what a model tracks in one pass (the prompt-analyzer red flag is >25 directives per section); overall token budget reasonable for the context it runs in (heavy is >~15% of the working context); mixed concerns ("what to do" tangled with "how to format") split apart.
- **Redundancy** — distinguish *intentional reinforcement* (a safety-critical rule repeated at 2-3 points of use, acceptable) from *copy-paste drift* (the same rule in many sections with wording that will diverge over time) and *structural redundancy* (the same thing stated in constraints AND examples AND troubleshooting). Flag a golden-rule candidate (a constraint appearing 3+ times) for extraction to a preamble.
- **Structure & flow** — a sane execution model (a linear or simply-accumulating pipeline is healthy; deep forward-reference chains and graph-like cross-references between steps are a smell); reference material (large tables, format specs, long examples) kept out of the step bodies.

## 3. Evidence sources & tooling

**Detect** whether the project (or the environment) ships the **`prompt-analyzer`** skill. If present, run its quantitative scan — `analyze_prompt.py <file>` (or `--format json`) — to get the token budget, per-section directive counts and density, the constraint-line count, the cross-reference graph + data-flow depth, and the redundancy groups. If it is **not** available, compute the same metrics inline: count RFC 2119 keywords per section, estimate tokens (~chars/4), and scan for repeated constraint lines — the framework is small and the numbers are the input to the qualitative judgment, not the verdict themselves. Do not impose the tool as a dependency; it is an accelerant, not a gate.

Gather in the parallel evidence pass, per file:

- **Quantitative scan (the accelerant):** the metrics above, from `analyze_prompt.py` when available or computed inline. These localize the heavy sections, the dense constraint blocks, and the redundancy groups so the qualitative read knows where to look.
- **Spec conformance check (the load-bearing step for SOPs):** read the file against the SOP specification — sections present and ordered, every step has a Constraints block, parameters well-formed and ordered, filename/extension correct. Each miss is a finding with the exact `file:line`.
- **Constraint-hygiene read:** for every directive, confirm it uses an RFC 2119 keyword at the right level; for every negative constraint, confirm a reason is stated inline. A negative constraint with no reason is the signature defect this audit exists to catch — record each one.
- **Consistency & clarity read:** cross-check instructions within the file (and, at consolidation, across sibling prompts) for contradictions, dead references, and ambiguity. Where the prompt references tools/steps, check they still exist (a light drift check; deep tool-drift is `eval-audit`).

Record the `file:line` (and the metric value where relevant) as the evidence pointer for every row. Prefer reading the actual prompt file over any summary of it.

## 4. Status scale + severity rubric

Status per row: **ok / warn / violation**.

- **Critical** — a defect that will make the model misbehave or silently ignore a rule: an internal **contradiction** between two instructions; a **negative constraint with no reason** on a safety- or correctness-critical rule; an instruction that references a tool/step/artifact that **no longer exists** (dead directive the model may still act on); an SOP missing a **required** section it needs to function.
- **Important** — degrades reliability without a guaranteed misfire: a **section overloaded** past ~25 directives (constraints will be dropped under load); **copy-paste drift** of a rule across sections (will diverge); a vague directive where an RFC 2119 level is needed; wrong requirement level (a SHOULD guarding something that must hold); parameters mis-ordered or not `snake_case`; a heavy token budget for the context.
- **Minor** — style and hygiene: a missing-but-recommended Examples/Troubleshooting section, a filename not in kebab-case, structural redundancy that merely wastes tokens, reference material inline that would read better in an appendix.

Suppressions must be explicit and recorded with a reason (e.g. "this safety rule is intentionally repeated at three points of use" — legitimate reinforcement, not drift; or "this prompt is a throwaway eval fixture, spec-conformance not required"). Never silently drop a row. Some findings are *interpretation notes*, not edits (e.g. "this redundancy is justified") — record those as policy in the report so they are not re-litigated next audit.

## 5. Fix patterns (and CI implications)

Prompt/SOP edits are **docs-level** changes, so they stay off the heavy code gates — **but a prompt is behavioral source**, so an edit that looks like a pure cleanup can change what the model does. State this up front and, for any load-bearing prompt, recommend a **behavioral re-check via `eval-audit`** (or the project's smoke/eval run) before the edit is trusted. Follow the repo conventions: keep prompt changes in **their own commit**, and the commit message must explain **why** the prompt changed, not only what.

- **Fix a contradiction / dead directive:** reconcile the two instructions or delete the stale one; if a tool/step was removed, remove every instruction that referenced it.
- **Repair constraint hygiene:** replace vague verbs with the right RFC 2119 keyword; add the missing **reason** to every negative constraint ("… because …" / "… since …"); downgrade/upgrade a mis-leveled requirement.
- **Bring an SOP to spec:** add the missing required section, give each step its Constraints block, fix parameter naming/ordering, rename to `.sop.md` / kebab-case.
- **Relieve load & redundancy:** split an overloaded section along its concerns (content-selection vs formatting); extract a 3+-times golden rule to a preamble and reference it; consolidate structural redundancy to one canonical location, keeping at most 2-3 deliberate reinforcements of a truly critical rule.
- **Restructure for flow:** move inline reference material to an appendix/examples; flatten deep forward-reference chains; where the load is intrinsic (a genuinely large workflow), note it as a **sub-agent decomposition** candidate rather than forcing it into one prompt (opt-in sub-audit below; hand the decomposition to the architecture owner).
- Docs-only outputs: the findings report and any prompt-quality policy notes.

## 6. Review dimensions (Phase-5 specialized reviewers)

- **Intent preservation** — the highest-value catch: does each edit keep the prompt's intended behavior? A cleanup that removes a load-bearing instruction, or "fixes" a contradiction by deleting the wrong side, is worse than the original. For a load-bearing prompt, this reviewer confirms a behavioral re-check was run or flags that it is still owed.
- **Spec conformance** — the edited SOP now actually matches the specification (sections, constraints blocks, parameter form), verified against the file, not asserted.
- **Constraint correctness** — every negative constraint now carries a reason; RFC 2119 levels are right and consistent; no new vague directive was introduced.
- **No new contradiction / drift** — the edit did not introduce a fresh internal contradiction or a reference to something that doesn't exist.

## 7. Opt-in sub-audits

- **Sub-agent decomposition analysis** — for an intrinsically overloaded prompt, apply the prompt-analyzer decomposition framework: identify natural split boundaries (context-independent steps, tool groupings, procedural-vs-analytical-vs-creative work), propose sub-agents with their handoff contracts, and produce the decomposition diagram. Enable via argument or ask the user; recommend it when a single prompt exceeds ~10K tokens or a section can't be split without splitting the agent.
- **Reasoning-token strategy** — classify each step by how much it benefits from extended thinking (high for multi-criteria judgment, cross-referencing, synthesis; low for fixed procedural calls) and recommend where reasoning tokens earn their cost. Ask the user; useful when tuning a reasoning-capable model.
- **Cross-prompt consistency sweep** — when the project has many prompts sharing conventions (a house style for tool descriptions, a shared safety preamble), audit them as a set for drift. Ask the user; useful before standardizing a prompt library.

## See also

- **[eval-audit](../eval-audit/SKILL.md)** — behavioral, model-level prompt quality (injection-resistance, drift-vs-tools, is-it-evaluated). Owns the "does it behave" half; this skill owns "is it well written." A load-bearing prompt edit wants both.
- **[security-audit](../security-audit/SKILL.md)** — prompt-injection as an application-security exposure; this skill only notes structural weaknesses and links.
- **[audit-core](../audit-core/SKILL.md)** — the shared engine and cross-cutting rules.
- The `/sop` skill (SOP specification) and the `/prompt-analyzer` skill (quantitative scan + qualitative framework) are the source materials this lens is built from.
