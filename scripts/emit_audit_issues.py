"""Turn a sweep's findings file into an importable GitHub issue set (#9).

The audit family produces two deliverables. The prose report has a template in
``audit/SKILL.md``; this module is the other half, the epic / child-epic /
sub-issue tree a maintainer can import into the audited project's tracker.

**The input is the findings file, never the report.** The report's per-domain
matrix is capped to the significant rows by design, so an emitter reading it
would silently drop exactly the findings the report judged too minor to print.
See ``docs/superpowers/specs/2026-09-16-issue-emitter-design.md``. The file
carries its provenance beside the findings, and a file without it is refused
unless ``--accept-missing-provenance`` is passed; ``provenance_problems``
says what it lacks.

Everything above ``main`` is pure: it takes findings and returns a tree of
issues. Creation lives in ``main`` behind an explicit flag, and the default is a
dry run that prints the tree and writes nothing anywhere.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

#: Severity order, worst first. Used for sorting and for the priority label.
#: A severity outside this set is not silently ranked last - ``_severity_rank``
#: raises, because an unknown severity in a findings file means the sweep and
#: this module disagree about the scale, and ranking it anywhere is a guess.
SEVERITIES = ("critical", "important", "minor")

#: The mutation that attaches a child issue to its parent. GitHub exposes
#: sub-issues only through GraphQL, so a link is not a ``gh issue`` subcommand
#: and cannot be spelled as one. It is here rather than inline so a test can
#: assert the plan carries it, which is the only way the link path is checked
#: without writing to somebody's tracker.
ADD_SUB_ISSUE = (
    "mutation($parent: ID!, $child: ID!) "
    "{ addSubIssue(input: {issueId: $parent, subIssueId: $child}) "
    "{ clientMutationId } }"
)

#: Priority label per severity. The audited project may not use these names, so
#: they are data rather than literals scattered through the rendering.
PRIORITY_LABELS = {
    "critical": "priority:urgent",
    "important": "priority:normal",
    "minor": "priority:low",
}

#: The longest issue body GitHub accepts. The command line is not the binding
#: constraint and is deliberately not guarded: a body at this limit is about 3%
#: of `ARG_MAX` on the platforms this runs on, so an argv long enough to be
#: refused by the kernel carries a body the API would have refused first.
MAX_BODY = 65536


class FindingsError(ValueError):
    """A findings file this module cannot read, with the reason."""


#: The top-level fields a findings file carries beside ``findings``, each the
#: machine-readable form of a line the report's "How the audit ran" section
#: prints, the ``Date`` line included. A file that lacks them cannot say which tree, which lenses or which
#: grants produced it, so a baseline diff cannot refuse to compare two refs and
#: a fold across runs rebuilds the header by hand. ``audit/SKILL.md`` states
#: the same list; the two are one contract.
PROVENANCE_FIELDS = ("target", "target_ref", "mode", "plugin", "grants", "generated")

#: What ``target_ref`` and ``grants`` hold. Each is a mapping rather than a
#: sentence, because the fields are there to be compared and a sentence such as
#: "c4f5daa9 (branch main, clean)" compares only as a string.
TARGET_REF_KEYS = ("commit", "branch", "dirty")
GRANT_KEYS = ("resolved-tree", "target-execution")


def provenance_problems(payload: Any) -> list[str]:
    """Every provenance field the payload lacks or carries in the wrong shape.

    Returns them all at once, for the reason ``Finding.from_mapping`` names
    every missing key: a file with five problems should take one run to fix,
    not five. An empty list means the provenance is complete.
    """
    if not isinstance(payload, dict):
        return [
            "the payload is a bare list, so it carries none of "
            + ", ".join(PROVENANCE_FIELDS)
        ]
    problems = []
    for name in ("target", "mode", "plugin", "generated"):
        value = payload.get(name)
        if not isinstance(value, str) or not value.strip():
            problems.append(f"{name} (a non-empty string)")
    ref = payload.get("target_ref")
    if not isinstance(ref, dict):
        problems.append("target_ref (a mapping of " + ", ".join(TARGET_REF_KEYS) + ")")
    else:
        commit = ref.get("commit")
        if not isinstance(commit, str) or not commit.strip():
            problems.append("target_ref.commit (a non-empty string)")
        # A detached HEAD has no branch, and that is a fact about the target
        # rather than a gap in the file, so null is the spelling for it.
        branch = ref.get("branch", "")
        if branch is not None and (not isinstance(branch, str) or not branch.strip()):
            problems.append(
                "target_ref.branch (a branch name, or null on a detached HEAD)"
            )
        if not isinstance(ref.get("dirty"), bool):
            problems.append("target_ref.dirty (true or false)")
    grants = payload.get("grants")
    if not isinstance(grants, dict):
        problems.append("grants (a mapping of " + ", ".join(GRANT_KEYS) + ")")
    else:
        problems += [
            f"grants.{key} (true or false)"
            for key in GRANT_KEYS
            if not isinstance(grants.get(key), bool)
        ]
        if (
            grants.get("target-execution") is True
            and grants.get("resolved-tree") is False
        ):
            problems.append(
                "grants (target-execution granted with resolved-tree withheld, "
                "which the execution grant implies)"
            )
    return problems


@dataclass(frozen=True)
class Finding:
    """One finding as the sweep recorded it."""

    domain: str
    check: str
    severity: str
    item: str
    evidence: str
    handbook: tuple[str, ...] = ()
    #: A caveat the domain attached to this finding - most often that it
    #: reported a check id it could not confirm. The consolidation rule
    #: requires such a caveat to travel with the id it qualifies, and this
    #: format is read by a machine that will not infer one, so it is a field
    #: rather than something the prose around the number carries.
    note: str = ""

    @staticmethod
    def from_mapping(raw: Any, *, where: str) -> Finding:
        """Build a finding, naming every missing key at once.

        Reporting one missing key at a time makes a malformed file take as
        many runs to fix as it has problems.
        """
        if not isinstance(raw, dict):
            raise FindingsError(
                f"{where}: expected a mapping, got {type(raw).__name__}"
            )
        required = ("domain", "check", "severity", "item", "evidence")
        missing = [k for k in required if not raw.get(k)]
        if missing:
            raise FindingsError(f"{where}: missing or empty {', '.join(missing)}")
        severity = str(raw["severity"]).strip().lower()
        if severity not in SEVERITIES:
            raise FindingsError(
                f"{where}: severity {raw['severity']!r} is not one of {', '.join(SEVERITIES)}"
            )
        handbook = raw.get("handbook") or ()
        if isinstance(handbook, str):
            handbook = (handbook,)
        return Finding(
            domain=str(raw["domain"]).strip(),
            check=str(raw["check"]).strip(),
            severity=severity,
            item=str(raw["item"]).strip(),
            evidence=str(raw["evidence"]).strip(),
            handbook=tuple(str(h).strip() for h in handbook),
            note=str(raw.get("note") or "").strip(),
        )


@dataclass(frozen=True)
class Issue:
    """One issue in the emitted tree."""

    title: str
    body: str
    labels: tuple[str, ...]
    children: tuple[Issue, ...] = field(default=())


def _severity_rank(severity: str) -> int:
    try:
        return SEVERITIES.index(severity)
    except ValueError as exc:  # guarded at construction
        raise FindingsError(f"unknown severity {severity!r}") from exc


def load_findings(payload: Any) -> list[Finding]:
    """Read a findings payload into `Finding` objects.

    Accepts either a mapping carrying a ``findings`` key, the shape a sweep
    writes with its provenance beside the findings, or a bare list. ``main``
    reads a bare list, or a mapping missing its provenance, only under
    ``--accept-missing-provenance``; this function reads the findings alone.
    """
    if isinstance(payload, dict):
        raw_list = payload.get("findings")
        if raw_list is None:
            raise FindingsError("mapping payload has no 'findings' key")
    else:
        raw_list = payload
    if not isinstance(raw_list, list):
        raise FindingsError(
            f"expected a list of findings, got {type(raw_list).__name__}"
        )
    return [
        Finding.from_mapping(raw, where=f"finding {i}")
        for i, raw in enumerate(raw_list)
    ]


def cluster(
    findings: list[Finding],
) -> list[tuple[tuple[str, str, str], list[Finding]]]:
    """Group findings into sub-issue clusters, one per (domain, check, severity).

    Returned in a stable order - domain, then severity worst-first, then check -
    so two runs over the same findings emit the same tree and a diff between
    them is a change in the findings rather than in the iteration order.
    """
    buckets: dict[tuple[str, str, str], list[Finding]] = {}
    for f in findings:
        buckets.setdefault((f.domain, f.check, f.severity), []).append(f)
    return sorted(
        buckets.items(),
        key=lambda kv: (kv[0][0], _severity_rank(kv[0][2]), kv[0][1]),
    )


def render_sub_issue(key: tuple[str, str, str], findings: list[Finding]) -> Issue:
    """Render one cluster as a sub-issue.

    Every finding contributes exactly one evidence line. That is the property
    that keeps clustering from losing data, and the tests assert it by counting
    evidence lines across the whole tree rather than per issue.
    """
    domain, check, severity = key
    plural = "finding" if len(findings) == 1 else "findings"
    title = f"[{domain}] {check}: {len(findings)} {severity} {plural}"
    lines = [
        f"Check `{check}` reported {len(findings)} {severity} {plural} in the `{domain}` domain.",
        "",
        "## Evidence",
    ]
    for f in findings:
        caveat = f" ({f.note})" if f.note else ""
        lines.append(f"- `{f.evidence}` - {f.item}{caveat}")
    citations = sorted({h for f in findings for h in f.handbook})
    lines += ["", "## Handbook"]
    if citations:
        lines += [f"- {c}" for c in citations]
    else:
        lines.append(
            "- No clause cited. The check record carries the citation; "
            "an empty list here means the sweep recorded none, not that none exists."
        )
    labels = (f"audit:{domain}", PRIORITY_LABELS[severity])
    return Issue(title=title, body="\n".join(lines), labels=labels)


def at_least(findings: list[Finding], floor: str) -> list[Finding]:
    """Findings at or above a severity floor, worst-first order preserved.

    The sweep's own report template offers filing issues at Important and
    above, so the tool it names has to be able to do that. The default is no
    floor, because dropping findings is the caller's decision to state rather
    than the emitter's to assume.
    """
    if floor not in SEVERITIES:
        raise FindingsError(f"unknown severity floor {floor!r}")
    limit = _severity_rank(floor)
    return [f for f in findings if _severity_rank(f.severity) <= limit]


def build_tree(findings: list[Finding], *, target: str) -> Issue:
    """Build the epic / child-epic / sub-issue tree.

    A domain with no findings gets no child epic, because an empty epic in a
    tracker reads as outstanding work rather than as a clean result. The report
    is what records a domain that came back clean.
    """
    clusters = cluster(findings)
    by_domain: dict[str, list[Issue]] = {}
    for key, group in clusters:
        by_domain.setdefault(key[0], []).append(render_sub_issue(key, group))

    domain_epics: list[Issue] = []
    for domain in sorted(by_domain):
        subs = by_domain[domain]
        counts = _severity_counts([f for k, g in clusters if k[0] == domain for f in g])
        body = "\n".join(
            [
                f"Productionization findings for the `{domain}` domain of `{target}`.",
                "",
                "| Severity | Findings |",
                "|---|---|",
                *[f"| {s} | {counts[s]} |" for s in SEVERITIES if counts[s]],
                "",
                f"{len(subs)} sub-issue(s) below.",
            ]
        )
        domain_epics.append(
            Issue(
                title=f"[{domain}] Productionization findings",
                body=body,
                labels=(f"audit:{domain}", "epic"),
                children=tuple(subs),
            )
        )

    total = _severity_counts(findings)
    root_body = "\n".join(
        [
            f"Handbook-conformance audit of `{target}`.",
            "",
            "| Severity | Findings |",
            "|---|---|",
            *[f"| {s} | {total[s]} |" for s in SEVERITIES],
            "",
            f"{len(domain_epics)} domain(s) with findings. "
            "Domains that came back clean carry no epic; the prose report records them.",
        ]
    )
    return Issue(
        title=f"Productionization of {target}",
        body=root_body,
        labels=("epic",),
        children=tuple(domain_epics),
    )


def _severity_counts(findings: list[Finding]) -> dict[str, int]:
    counts = dict.fromkeys(SEVERITIES, 0)
    for f in findings:
        counts[f.severity] += 1
    return counts


def labels_used(tree: Issue) -> list[str]:
    """Every label the tree needs, sorted. What `--create` would ensure exists."""
    seen: set[str] = set()

    def walk(issue: Issue) -> None:
        seen.update(issue.labels)
        for child in issue.children:
            walk(child)

    walk(tree)
    return sorted(seen)


def oversized(tree: Issue) -> list[tuple[str, int]]:
    """Every issue whose body GitHub would refuse, with the length it refuses.

    Clustering puts every finding of one `(domain, check, severity)` group into
    one body, so a check with enough findings at one severity produces a body
    no API call will accept. That is answered here rather than at the write,
    because a cluster discovered mid-run fails after the epics are already in
    the target and the duplicate guard then refuses every retry - the shape
    that costs the operator a half-filed tree in a repository they do not own.
    """
    found = [(tree.title, len(tree.body))] if len(tree.body) > MAX_BODY else []
    for child in tree.children:
        found += oversized(child)
    return found


def render_dry_run(tree: Issue) -> str:
    """Render the whole tree as text, the way `--dry-run` prints it."""
    out: list[str] = []

    def walk(issue: Issue, depth: int) -> None:
        pad = "  " * depth
        out.append(f"{pad}{'#' * (depth + 1)} {issue.title}")
        out.append(f"{pad}labels: {', '.join(issue.labels)}")
        for line in issue.body.splitlines():
            out.append(f"{pad}| {line}")
        out.append("")
        for child in issue.children:
            walk(child, depth + 1)

    walk(tree, 0)
    out.append(f"labels required: {', '.join(labels_used(tree))}")
    out.append(f"issues that would be created: {_count(tree)}")
    return "\n".join(out)


def _count(issue: Issue) -> int:
    return 1 + sum(_count(c) for c in issue.children)


@dataclass(frozen=True)
class Action:
    """One write the creation path would perform, as data rather than as a call.

    Planning and performing are split so the decisions - which labels are
    missing, what order issues are created in, which parent each child links to
    - are testable without a network, a token, or a repository to write to.
    The executor below is the only part that cannot be tested that way, and it
    is deliberately thin enough to read in one sitting.
    """

    kind: str  # "create-label" | "create-issue" | "link-sub-issue"
    argv: tuple[str, ...]
    #: What this action does, in words, for the executor to name when it fails.
    #: The argv cannot stand in: it carries the issue body, so a failure that
    #: printed it would bury the message under the whole document - 70 KB of it
    #: in the run that found this, which is why the field exists.
    describes: str = ""
    #: Index into the plan's own issue order, for a link whose target is an
    #: issue this plan has not created yet. Resolved by the executor from the
    #: numbers the create calls return, never guessed.
    parent_ref: int | None = None
    self_ref: int | None = None


def plan_labels(tree: Issue, existing: set[str], *, target: str) -> list[Action]:
    """Label creations needed, skipping those that already exist.

    Idempotent by construction: the plan is a set difference, so running the
    emitter twice against the same repository plans nothing the second time.

    **Compared case-insensitively**, because GitHub treats label names that way
    for uniqueness. A tracker holding `Epic` already has this tree's `epic`, and
    planning it anyway makes the creation 422 and take the whole run down with
    it before a single issue is opened - the tree needs `epic` every time, so
    that is not an edge case but the ordinary one on any repository that
    capitalises its labels.
    """
    have = {name.casefold() for name in existing}
    return [
        Action(
            kind="create-label",
            argv=("gh", "label", "create", name, "--repo", target),
            describes=f"creating the label {name!r}",
        )
        for name in labels_used(tree)
        if name.casefold() not in have
    ]


def plan_issues(tree: Issue, *, target: str) -> list[Action]:
    """Issue creations and parent links, parents before children.

    Order matters and is the whole reason this is a plan rather than a
    recursion with side effects: a sub-issue cannot be linked to a parent that
    does not exist yet, so every create is emitted before the link that uses it.
    """
    actions: list[Action] = []
    counter = 0

    def walk(issue: Issue, parent_index: int | None) -> None:
        nonlocal counter
        index = counter
        counter += 1
        label_args = [arg for name in issue.labels for arg in ("--label", name)]
        actions.append(
            Action(
                kind="create-issue",
                argv=(
                    "gh",
                    "issue",
                    "create",
                    "--repo",
                    target,
                    "--title",
                    issue.title,
                    "--body",
                    issue.body,
                    *label_args,
                ),
                self_ref=index,
                describes=f"creating the issue {issue.title!r}",
            )
        )
        if parent_index is not None:
            actions.append(
                Action(
                    kind="link-sub-issue",
                    argv=("gh", "api", "graphql", "-f", f"query={ADD_SUB_ISSUE}"),
                    parent_ref=parent_index,
                    self_ref=index,
                    describes=f"linking {issue.title!r} under its parent",
                )
            )
        for child in issue.children:
            walk(child, index)

    walk(tree, None)
    return actions


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Emit an importable issue set from a sweep's findings file."
    )
    parser.add_argument(
        "findings", type=Path, help="path to the findings JSON the sweep wrote"
    )
    parser.add_argument(
        "--target", required=True, help="the audited repository, as owner/name"
    )
    parser.add_argument(
        "--min-severity",
        choices=SEVERITIES,
        help=(
            "drop findings below this severity. Omit to emit every finding; "
            "the sweep's report template offers Important and above."
        ),
    )
    parser.add_argument(
        "--accept-missing-provenance",
        action="store_true",
        help=(
            "read a findings file written before its provenance fields were "
            "required. The dry run says it was used and what the file lacks."
        ),
    )
    parser.add_argument(
        "--create",
        action="store_true",
        help=(
            "create the issues and any missing labels in --target. Without this "
            "nothing is created and nothing is written anywhere."
        ),
    )
    args = parser.parse_args(argv)

    try:
        payload = json.loads(args.findings.read_text())
    except FileNotFoundError:
        print(
            f"error: no findings file at {args.findings}. "
            "The sweep writes one; this tool does not read the prose report, "
            "whose findings matrix is capped to the significant rows.",
            file=sys.stderr,
        )
        return 2
    except json.JSONDecodeError as exc:
        print(f"error: {args.findings} is not valid JSON: {exc}", file=sys.stderr)
        return 2

    lacking = provenance_problems(payload)
    if lacking and not args.accept_missing_provenance:
        print(
            f"error: {args.findings} lacks its provenance: {'; '.join(lacking)}. "
            "A sweep writes these beside the findings; pass "
            "--accept-missing-provenance to read a file written before they "
            "were required.",
            file=sys.stderr,
        )
        return 2
    if args.accept_missing_provenance:
        print(
            "provenance: --accept-missing-provenance was passed; "
            + (
                f"the file lacks {'; '.join(lacking)}"
                if lacking
                else "the file's provenance is complete, so it accepted nothing"
            )
        )

    try:
        findings = load_findings(payload)
    except FindingsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.min_severity:
        kept = at_least(findings, args.min_severity)
        print(
            f"severity floor {args.min_severity}: "
            f"{len(kept)} of {len(findings)} findings kept",
            file=sys.stderr,
        )
        findings = kept

    if not findings:
        # An empty tree is a root epic with no children, and creating one is
        # worse than doing nothing: it is titled from --target, so the
        # duplicate guard would read it as an existing tree and refuse the
        # later run that actually has findings to file. The reachable case is
        # the documented one - --min-severity important over a sweep whose
        # findings are all Minor - rather than an empty findings file.
        print(
            "no findings to file"
            + (f" at {args.min_severity} or above" if args.min_severity else "")
            + ". Nothing emitted, and nothing would be created."
        )
        return 0

    tree = build_tree(findings, target=args.target)
    too_long = oversized(tree)

    if not args.create:
        print(render_dry_run(tree))
        plan = plan_labels(tree, set(), target=args.target) + plan_issues(
            tree, target=args.target
        )
        # Counted as what --create would do, which is nothing at all when a
        # body is over the limit. A dry run that promised 24 writes and was
        # then refused would have been the misleading half of this.
        print(f"writes that --create would perform: {0 if too_long else len(plan)}")

    if too_long:
        for title, length in too_long:
            print(
                f"error: the body for {title!r} is {length} characters and "
                f"GitHub refuses anything over {MAX_BODY}.",
                file=sys.stderr,
            )
        print(
            "Nothing was created. A severity floor does not reduce one of "
            "these: a cluster is one severity by construction, so --min-"
            "severity either keeps it whole or drops it entirely. File that "
            "cluster by hand, or raise the floor above it and file the rest.",
            file=sys.stderr,
        )
        return 7

    if not args.create:
        return 0

    return _execute(tree, target=args.target)


def _execute(tree: Issue, *, target: str) -> int:
    """Perform the plan against a real repository.

    The writes themselves cannot be tested here - every one of them writes to a
    repository this project does not own - so what this function does around
    them is the part that is tested: the order, the node ids the links need,
    and what it reports when a write fails partway through.

    That last one is why this is no longer thin. A run that dies on its third
    write has already put a root epic and a domain epic in somebody else's
    tracker, and the duplicate guard will then refuse every retry, so failing
    silently and letting the exception out leaves the operator with orphan
    issues, a stack trace, and no way to tell which issue is blocking them.
    """
    import subprocess

    # `gh label list` pages at 30 by default, so a repository with more labels
    # than that would report the rest as missing and this would try to create
    # them. Ask for all of them, and refuse to proceed on a listing that failed
    # rather than treating "no labels found" as "no labels exist".
    probe = subprocess.run(
        (
            "gh",
            "label",
            "list",
            "--repo",
            target,
            "--limit",
            "1000",
            "--json",
            "name",
            "--jq",
            ".[].name",
        ),
        capture_output=True,
        text=True,
        check=False,
    )
    if probe.returncode != 0:
        print(
            f"error: could not list labels in {target}: {probe.stderr.strip()}. "
            "Refusing to create labels against an unknown set, because every "
            "existing one would look missing.",
            file=sys.stderr,
        )
        return 4
    existing = {line.strip() for line in probe.stdout.splitlines() if line.strip()}

    # A second run would open the whole tree again, and nothing about an issue
    # says it was emitted by this tool, so the duplicate is invisible until
    # somebody reads the tracker.
    # Listed rather than searched, and paginated rather than capped.
    # `--search` hits the Search API, which is eventually consistent and
    # tokenizes its query, so a tree created moments ago - the retry case this
    # guard exists for - can come back absent. `gh issue list` is consistent but
    # pages newest-first under a limit, and a truncated page still exits 0, so
    # an epic old enough to fall off the end reads as absent through the very
    # branch that refuses a failed listing. `--paginate` walks every page, and
    # pull requests are filtered out because that endpoint returns them too and
    # a PR sharing the title is not the tree.
    root = tree.title
    seen = subprocess.run(
        (
            "gh",
            "api",
            f"repos/{target}/issues?state=all&per_page=100",
            "--paginate",
            "--jq",
            ".[] | select(.pull_request == null) | .title",
        ),
        capture_output=True,
        text=True,
        check=False,
    )
    if seen.returncode != 0:
        print(
            f"error: could not search {target} for an existing tree: "
            f"{seen.stderr.strip()}. Refusing to proceed. A search that failed "
            "is not a search that found nothing, and the difference between "
            "them is whether this run duplicates the whole tree.",
            file=sys.stderr,
        )
        return 4
    titles = {line.strip() for line in seen.stdout.splitlines() if line.strip()}
    # Compared case-insensitively, for the same reason `plan_labels` is. The
    # root title embeds `--target` verbatim and GitHub resolves `owner/repo`
    # case-insensitively, so `Owner/Repo` and `owner/repo` are one repository
    # whose two runs produce two differently-cased titles. An exact match reads
    # the second as a new tree and files the whole thing again, which is a
    # duplicate in the tracker this guard exists to protect - worse than the
    # 422 the label rule avoids, and silent where that one is loud.
    if root.casefold() in {title.casefold() for title in titles}:
        print(
            f"error: {target} already has an issue titled {root!r}. "
            "This tool does not reconcile with an existing tree, so a second "
            "run would duplicate it. Closing that epic does not clear this: "
            "the check reads open and closed alike, because a closed epic "
            "still means the tree was filed. Removing that epic alone does not "
            "make the repository ready either: GitHub keeps a sub-issue when "
            "its parent goes, so the children stay and the next run files a "
            "second copy of them beside the originals. Either delete the whole "
            "existing tree, epic and children, or leave it in place and add "
            "what is missing by hand.",
            file=sys.stderr,
        )
        return 5

    #: Every issue this run has opened, in creation order, as (number, title).
    #: The first is the root epic, which is what the duplicate guard reads, so
    #: a partial run can tell the operator exactly which issue is blocking the
    #: retry rather than leaving them to work it out.
    created: list[tuple[str, str]] = []

    def stopped(action: Action, stderr: str) -> int:
        """Report a write that failed, and what it left behind.

        The argv is never printed. It carries the issue body, so the traceback
        this replaces buried the message under the whole document. What the
        operator needs instead is three things: which write failed, what the
        tool said about it, and what is now sitting in a repository this
        project does not own.
        """
        print(f"error: {action.describes} failed: {stderr}", file=sys.stderr)
        if not created:
            print(f"Nothing was created in {target}.", file=sys.stderr)
            return 6
        print(
            f"{len(created)} issue(s) were created in {target} before this "
            "failed, and they are still there:",
            file=sys.stderr,
        )
        for number, title in created:
            print(f"  #{number} {title}", file=sys.stderr)
        root_number, root_title = created[0]
        print(
            f"The tree is partial, and re-running will not resume it: the "
            f"duplicate guard reads #{root_number}, {root_title!r}, as a tree "
            "already filed and refuses. Closing it does not clear that, for "
            "the same reason. To file the whole tree again, delete every issue "
            "listed above and not only the root: GitHub keeps a sub-issue when "
            "its parent goes, so removing the epic alone leaves the rest in "
            "place and the retry files a second copy of them. Otherwise file "
            "what is missing by hand against the part that is there.",
            file=sys.stderr,
        )
        return 6

    def run(argv: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
        """One write, with its output captured rather than printed.

        Captured because the link is a GraphQL mutation whose response is a
        line of JSON per call, and printing those told the operator nothing
        while hiding what had actually been created.
        """
        return subprocess.run(argv, capture_output=True, text=True, check=False)

    for action in plan_labels(tree, existing, target=target):
        done = run(action.argv)
        if done.returncode != 0:
            return stopped(action, done.stderr.strip())

    node_ids: dict[int, str] = {}
    for action in plan_issues(tree, target=target):
        if action.kind == "create-issue":
            done = run(action.argv)
            if done.returncode != 0:
                return stopped(action, done.stderr.strip())
            url = done.stdout.strip().splitlines()[-1]
            number = url.rsplit("/", 1)[-1]
            # Keyed on the flag rather than on a position, so adding an
            # argument ahead of it does not silently record the wrong string.
            title = action.argv[action.argv.index("--title") + 1]
            created.append((number, title))
            ident = run(
                (
                    "gh",
                    "issue",
                    "view",
                    number,
                    "--repo",
                    target,
                    "--json",
                    "id",
                    "--jq",
                    ".id",
                )
            )
            if ident.returncode != 0:
                return stopped(action, ident.stderr.strip())
            node_ids[action.self_ref] = ident.stdout.strip()
        elif action.kind == "link-sub-issue":
            done = run(
                (
                    *action.argv,
                    "-f",
                    f"parent={node_ids[action.parent_ref]}",
                    "-f",
                    f"child={node_ids[action.self_ref]}",
                )
            )
            if done.returncode != 0:
                return stopped(action, done.stderr.strip())

    # A dry run tells the operator exactly what it would do; without this the
    # real run told them less than that, and gave them no numbers to check.
    print(f"created {len(created)} issue(s) in {target}:")
    for number, title in created:
        print(f"  #{number} {title}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
