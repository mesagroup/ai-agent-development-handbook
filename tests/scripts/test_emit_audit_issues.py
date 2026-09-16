"""Tests for scripts/emit_audit_issues.py (#9).

The module's whole value is that clustering is mechanical, so these tests are
mostly about the three properties the spec names: same check and severity
merge, same check and different severity split, and no evidence line is ever
lost. The last one is the conservation property, and it is asserted over the
whole tree rather than per issue, because a clustering bug that drops a finding
would otherwise pass every per-issue assertion.

The creation path is planned as data and executed elsewhere. What is testable
is the plan - which labels are missing, what order the creates go in, which
parent each link points at - and that is what is tested here. Nothing in this
file performs a write or reaches a network.
"""

from __future__ import annotations

import json

import emit_audit_issues as em
import pytest


def _finding(**over: object) -> dict[str, object]:
    base: dict[str, object] = {
        "domain": "security",
        "check": "security/secrets-in-code",
        "severity": "critical",
        "item": "an AWS key literal",
        "evidence": "src/app.py:14",
        "handbook": ["security/never-commit-a-secret"],
    }
    base.update(over)
    return base


def _load(*raw: dict[str, object]) -> list[em.Finding]:
    return em.load_findings(list(raw))


def test_two_findings_of_one_check_at_one_severity_become_one_issue():
    findings = _load(
        _finding(), _finding(evidence="src/cfg.py:3", item="a token literal")
    )
    tree = em.build_tree(findings, target="some-org/some-repo")
    subs = tree.children[0].children
    assert len(subs) == 1
    assert "2 critical findings" in subs[0].title


def test_two_findings_of_one_check_at_different_severities_split():
    findings = _load(_finding(), _finding(severity="minor", evidence="src/doc.py:9"))
    tree = em.build_tree(findings, target="some-org/some-repo")
    subs = tree.children[0].children
    assert len(subs) == 2
    assert [s.title.split(": ")[1] for s in subs] == [
        "1 critical finding",
        "1 minor finding",
    ]


def test_no_evidence_line_is_lost_however_the_findings_cluster():
    """The conservation property.

    Counted over the whole tree, because a bug that dropped a finding from one
    cluster would still leave every individual issue internally consistent.
    """
    raw = [
        _finding(evidence=f"src/a.py:{i}", severity=sev, check=check, domain=dom)
        for i, (sev, check, dom) in enumerate(
            [
                ("critical", "security/secrets-in-code", "security"),
                ("critical", "security/secrets-in-code", "security"),
                ("minor", "security/secrets-in-code", "security"),
                ("important", "deps/vulnerabilities", "deps"),
                ("important", "deps/vulnerabilities", "deps"),
                ("minor", "docs/coverage", "docs"),
            ]
        )
    ]
    findings = _load(*raw)
    tree = em.build_tree(findings, target="some-org/some-repo")

    evidence_lines = 0
    stack = [tree]
    while stack:
        issue = stack.pop()
        evidence_lines += sum(
            1 for line in issue.body.splitlines() if line.startswith("- `src/a.py:")
        )
        stack.extend(issue.children)
    assert evidence_lines == len(raw)


def test_a_domain_with_no_findings_gets_no_epic():
    tree = em.build_tree(_load(_finding()), target="some-org/some-repo")
    assert [c.title for c in tree.children] == ["[security] Productionization findings"]


def test_the_tree_is_stable_across_runs_over_the_same_findings():
    raw = [
        _finding(domain="deps", check="deps/licenses", severity="minor"),
        _finding(domain="security", check="security/injection", severity="important"),
        _finding(domain="deps", check="deps/vulnerabilities", severity="critical"),
    ]
    first = em.render_dry_run(em.build_tree(_load(*raw), target="t/t"))
    second = em.render_dry_run(em.build_tree(_load(*reversed(raw)), target="t/t"))
    assert first == second


def test_severity_decides_the_priority_label():
    tree = em.build_tree(
        _load(
            _finding(severity="critical"), _finding(severity="minor", evidence="b.py:1")
        ),
        target="t/t",
    )
    labels = {lbl for sub in tree.children[0].children for lbl in sub.labels}
    assert {"priority:urgent", "priority:low", "audit:security"} <= labels


def test_a_missing_required_key_names_every_missing_one_at_once():
    with pytest.raises(em.FindingsError) as caught:
        em.load_findings([{"domain": "security"}])
    message = str(caught.value)
    for key in ("check", "severity", "item", "evidence"):
        assert key in message


def test_a_severity_outside_the_scale_is_refused_rather_than_ranked_last():
    """An unknown severity means the sweep and this module disagree about the
    scale, and placing it anywhere in the order would be a guess that reads as
    a decision."""
    with pytest.raises(em.FindingsError, match="blocker"):
        em.load_findings([_finding(severity="blocker")])


def test_a_payload_may_carry_metadata_beside_its_findings():
    findings = em.load_findings({"target": "t/t", "findings": [_finding()]})
    assert len(findings) == 1


def test_a_mapping_without_a_findings_key_is_refused_by_name():
    with pytest.raises(em.FindingsError, match="findings"):
        em.load_findings({"target": "t/t"})


def test_handbook_citations_are_deduplicated_within_a_cluster():
    findings = _load(_finding(), _finding(evidence="src/b.py:2"))
    sub = em.build_tree(findings, target="t/t").children[0].children[0]
    assert sub.body.count("security/never-commit-a-secret") == 1


def test_a_cluster_with_no_citation_says_so_rather_than_leaving_the_section_empty():
    findings = _load(_finding(handbook=[]))
    sub = em.build_tree(findings, target="t/t").children[0].children[0]
    assert "No clause cited" in sub.body


def test_a_label_that_already_exists_is_not_planned_again():
    """Idempotency is a set difference, so a second run plans nothing."""
    tree = em.build_tree(_load(_finding()), target="t/t")
    everything = set(em.labels_used(tree))
    assert em.plan_labels(tree, everything, target="t/t") == []
    assert len(em.plan_labels(tree, set(), target="t/t")) == len(everything)


def test_every_parent_is_created_before_the_link_that_uses_it():
    """The ordering property. A sub-issue cannot be linked to a parent that does
    not exist yet, so a plan that emitted a link first would fail at the point
    where it is hardest to recover, half way through writing to a repository."""
    tree = em.build_tree(
        _load(
            _finding(),
            _finding(
                domain="deps",
                check="deps/licenses",
                severity="minor",
                evidence="u.lock:1",
            ),
        ),
        target="t/t",
    )
    created: set[int] = set()
    links = 0
    for action in em.plan_issues(tree, target="t/t"):
        if action.kind == "create-issue":
            created.add(action.self_ref)
        else:
            links += 1
            assert action.parent_ref in created
            assert action.self_ref in created
    assert links == em._count(tree) - 1


def test_the_dry_run_names_every_label_it_would_need():
    tree = em.build_tree(_load(_finding()), target="t/t")
    rendered = em.render_dry_run(tree)
    for label in em.labels_used(tree):
        assert label in rendered


def test_the_cli_creates_nothing_without_the_flag(tmp_path, capsys):
    path = tmp_path / "findings.json"
    path.write_text(json.dumps({"findings": [_finding()]}))
    assert em.main([str(path), "--target", "some-org/some-repo"]) == 0
    out = capsys.readouterr().out
    assert "Productionization of some-org/some-repo" in out
    assert "writes that --create would perform:" in out


def test_a_missing_findings_file_says_it_will_not_fall_back_to_the_report(
    tmp_path, capsys
):
    """The fallback that does not exist is the point.

    Reading the prose report instead would silently drop every row the report
    capped away, which is the failure the input contract exists to prevent, so
    the error names it rather than only reporting a missing path.
    """
    code = em.main([str(tmp_path / "absent.json"), "--target", "t/t"])
    assert code == 2
    assert "capped to the significant rows" in capsys.readouterr().err


def test_malformed_json_is_reported_as_such(tmp_path, capsys):
    path = tmp_path / "findings.json"
    path.write_text("{not json")
    assert em.main([str(path), "--target", "t/t"]) == 2
    assert "not valid JSON" in capsys.readouterr().err


def test_a_severity_floor_keeps_that_severity_and_everything_worse():
    findings = _load(
        _finding(severity="critical"),
        _finding(severity="important", evidence="b.py:1"),
        _finding(severity="minor", evidence="c.py:1"),
    )
    kept = em.at_least(findings, "important")
    assert [f.severity for f in kept] == ["critical", "important"]


def test_no_floor_keeps_everything():
    findings = _load(_finding(severity="minor"))
    assert em.at_least(findings, "minor") == findings


def test_an_unknown_floor_is_refused():
    with pytest.raises(em.FindingsError, match="blocker"):
        em.at_least(_load(_finding()), "blocker")


def test_a_caveat_travels_with_the_finding_it_qualifies():
    """The consolidation rule requires a caveat to travel with an id the
    domain could not confirm, and a machine-read format will not infer one."""
    findings = _load(_finding(note="check id unconfirmed by the domain"))
    sub = em.build_tree(findings, target="t/t").children[0].children[0]
    assert "check id unconfirmed by the domain" in sub.body


def test_a_link_action_carries_the_mutation_that_performs_it():
    """The link is the tree.

    A plan whose link actions carry no command produces a flat dump of issues
    with no parent anywhere, which is the deliverable's whole shape lost while
    every individual issue looks right.
    """
    tree = em.build_tree(
        _load(
            _finding(),
            _finding(
                domain="deps", check="deps/licenses", severity="minor", evidence="u:1"
            ),
        ),
        target="t/t",
    )
    links = [
        a for a in em.plan_issues(tree, target="t/t") if a.kind == "link-sub-issue"
    ]
    assert links
    for action in links:
        assert action.argv, "a link action with no argv performs no link"
        assert "addSubIssue" in " ".join(action.argv)


def test_a_label_is_never_created_with_force():
    """`--force` overwrites an existing label's colour and description, which
    turns a listing that missed a page into silent edits to somebody's repo."""
    tree = em.build_tree(_load(_finding()), target="t/t")
    for action in em.plan_labels(tree, set(), target="t/t"):
        assert "--force" not in action.argv


def test_an_existing_label_in_another_case_is_not_planned_again():
    """GitHub label names are case-insensitive for uniqueness.

    The tree needs `epic` on every run, so a tracker that capitalises its
    labels would 422 on the first creation and take the run down before a
    single issue was opened.
    """
    tree = em.build_tree(_load(_finding()), target="t/t")
    shouty = {name.upper() for name in em.labels_used(tree)}
    assert em.plan_labels(tree, shouty, target="t/t") == []
