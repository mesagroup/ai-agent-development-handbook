# Documentation

| Area | What is in it |
|------|---------------|
| [`goal.md`](goal.md) | **What this repository delivers**, as outcomes with stable ids that every issue's `Serves:` line names, the categories of work that do not count, and the done condition. The tracker is held against it. |
| [`engineering/`](engineering/README.md) | **The handbook.** Ten parts covering the life of a change, from problem framing through evaluation to operation. Normative prose; the source of every claim the audit skills check. Ships as a standalone HTML artifact via `scripts/render_handbook_artifact.py`. |
| [`engineering-notes.md`](engineering-notes.md) | Practices true enough to write down but too contingent on one execution environment to be normative. The cutting-room floor, with the reason each was cut. |
| [`audit/`](audit/README.md) | The traceability matrix: every handbook section mapped onto the checks that cover it, with a class and severity per clause and the gap list ordered by severity. |
| [`stories/`](stories/) | Narrative records of completed work: what was built, what the data showed, what transferred. |
| [`superpowers/`](superpowers/) | Process artifacts. `specs/` holds approved designs, `plans/` holds the implementation plans executed from them. |

## Where to start

Reading the handbook: [`engineering/README.md`](engineering/README.md).

Understanding what the audit skills can and cannot see: [`audit/handbook-traceability.md`](audit/handbook-traceability.md). The severity × coverage cross-tab answers which high-risk clauses nothing currently checks, which is the queue the skill family works from.
