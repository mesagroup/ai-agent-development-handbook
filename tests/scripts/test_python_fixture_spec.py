"""Tests for scripts/python_fixture_spec.py and its renderer (#45)."""

import importlib.util
import re
import tomllib
from pathlib import Path

import pytest
import python_fixture_spec
from audit_checks import (
    SKILLS_DIR,
    _languages_whose_tools_all_need_a_grant,
    _routes_answering_ungranted,
    load_checks,
)
from python_fixture_spec import (
    DEPENDENCIES,
    DEPS_CHECKS,
    EXPECTATIONS,
    FORMS,
    FULL_PARTITION,
    PACKAGE,
    PARTITIONS,
    SOURCE_FILES,
    THIN_EXTRA_CHECK,
    VERIFIED_ON,
    declared,
    expectations_for,
    render_manifests,
    source_tree,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_RENDERER = _REPO_ROOT / "scripts" / "render_python_fixture_expectations.py"
_RECORD = _REPO_ROOT / "docs" / "audit" / "python-fixture-expectations.md"


def _load_renderer():
    """Load the renderer by path, as `tests/scripts/` does for every script."""
    spec = importlib.util.spec_from_file_location(
        "render_python_fixture_expectations", _RENDERER
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _table_rows(text: str, header: str) -> list[str]:
    """The body rows of the one table whose header line is `header`.

    Located by its header rather than by counting pipes across the document, so
    a row added to another table cannot be mistaken for one of these.
    """
    lines = text.splitlines()
    start = lines.index(header) + 2  # skip the header and its separator
    rows = []
    for line in lines[start:]:
        if not line.startswith("|"):
            break
        rows.append(line)
    return rows


# A dotted name a claim uses to point at seeded code, and a seeded test file with
# an optional `::function` selector. Both are resolved against the tree rather
# than read, because a claim naming a symbol the tree no longer has is the exact
# shape of a seed that was renamed away with nothing to notice.
_DOTTED_NAME = re.compile(rf"{PACKAGE}(?:\.\w+)+")
_TEST_REF = re.compile(r"(tests/test_\w+\.py)(?:::(\w+))?")


def _python_lens_records() -> set[str]:
    """Every check record in the family that names a Python tool.

    Read from the records rather than listed here: the fixture round exercises
    the `python:` tooling entries, written as frontmatter or projected from
    routes, so the set it covers is whatever the family currently names rather
    than a copy taken when this was written.

    A record can carry a `lang: python` route and still sit outside this set,
    because a route naming no tool prescribes a reading rather than a command,
    and the harness runs literal shell commands - there is nothing to seed an
    expectation for. So the population is the tool-naming records, and a
    tool-less route's absence from the fixture round is the shape of the round
    rather than a seed that went missing. Read "whatever the family declares"
    as the tools it declares, which is the only part a seeded tree can answer.
    """
    checks, errors = load_checks(SKILLS_DIR)
    assert not errors, errors
    return {cid for cid, check in checks.items() if check.tooling.get("python")}


def test_every_dependency_name_is_a_bare_toml_key():
    """A dotted distribution name silently becomes a nested TOML table.

    The poetry and Pipfile renderers write `name = "pin"`, so a name such as
    `ruamel.yaml` parses as a table `ruamel` containing `yaml` rather than as
    one dependency. `tomllib` accepts it, every substring assertion here accepts
    it, and the manager reads a dependency that does not exist. The set is meant
    to be edited whenever a pin is re-verified, so this guards the next edit
    rather than the current contents.
    """
    for dependency in DEPENDENCIES:
        assert re.fullmatch(r"[A-Za-z0-9_-]+", dependency.name), dependency.name


def test_every_seed_is_carried_by_exactly_one_dependency():
    seeds = [s for d in DEPENDENCIES for s in d.seeds]
    assert sorted(seeds) == sorted(set(seeds))
    assert "vulnerable" in seeds and "copyleft" in seeds


def test_the_undeclared_import_is_imported_and_not_declared():
    undeclared = [d for d in DEPENDENCIES if not d.pin]
    assert [d.name for d in undeclared] == ["markupsafe"]
    assert undeclared[0].imported is True


def test_the_unused_dependency_is_declared_and_never_imported():
    unused = [d for d in DEPENDENCIES if d.pin and not d.imported]
    assert [d.name for d in unused] == ["six"]
    body = "\n".join(f.body for f in SOURCE_FILES)
    assert "import six" not in body


def test_the_five_partitions_are_named():
    assert PARTITIONS == ("uv", "pip", "poetry", "pipenv", "pylock")


def test_every_imported_dependency_is_imported_somewhere_in_the_tree():
    """The positive direction of the import claim.

    The unused seed's direction is guarded above by the absence of a string.
    This one guards the rest: deleting `import markupsafe` from the seeded
    source would otherwise retire the DEP003 seed while the dataclass and the
    expectation both went on claiming it. The module name is checked rather
    than the distribution name because they differ - `Unidecode` imports as
    `unidecode`.
    """
    body = "\n".join(f.body for f in SOURCE_FILES)
    for dependency in DEPENDENCIES:
        if dependency.imported:
            assert f"import {dependency.module}" in body, dependency.name


def test_source_tree_maps_paths_to_bodies():
    tree = source_tree()
    assert "src/fixture_app/domain/model.py" in tree
    assert tree["src/fixture_app/domain/model.py"].startswith('"""')


def test_source_tree_loses_no_file_to_a_duplicate_path():
    """Two SourceFile entries sharing a path would collapse into one.

    The body and the seeds of whichever came first would vanish with no error,
    and Task 5 merges this dict with the manifests, where a collision is
    equally silent.
    """
    assert len(source_tree()) == len(SOURCE_FILES)


def test_every_partition_renders_a_manifest():
    for partition in PARTITIONS:
        files = render_manifests(partition)
        assert files, partition
        assert all(body.strip() for body in files.values()), partition


def test_the_undeclared_dependency_reaches_no_manifest():
    """Derived from the definition rather than naming the package.

    Written against the literal string, this test goes on passing after the
    undeclared seed is swapped for another package - it would then assert that a
    name nothing renders is absent, which nothing can fail.
    """
    undeclared = [d.name.lower() for d in DEPENDENCIES if not d.pin]
    assert undeclared, "the undeclared-import seed has gone missing"
    for partition in PARTITIONS:
        for body in render_manifests(partition).values():
            for name in undeclared:
                assert name not in body.lower(), (partition, name)


def test_each_partition_uses_its_own_manifest_format():
    assert "pyproject.toml" in render_manifests("uv")
    assert "requirements.txt" in render_manifests("pip")
    assert "tool.poetry" in render_manifests("poetry")["pyproject.toml"]
    assert "Pipfile" in render_manifests("pipenv")


def test_the_requirements_partitions_declare_nothing_in_a_project_table():
    """The silencing declaration, which the competing-declaration guard misses.

    A `[project]` table carrying build metadata and no `dependencies` key is not
    silent about dependencies: it is an affirmative claim of zero. deptry reads
    it in preference to `requirements.txt` and then reports the real
    dependencies as DEP001 while the DEP002 seed disappears entirely, so the
    partition produces a full result from the wrong file.

    The guard against two files *declaring* the set cannot see this, because the
    offending table declares nothing - which is exactly what makes it wrong. So
    `pip` and `pipenv` are held to rendering no `pyproject.toml` at all.
    """
    for partition in ("pip", "pipenv"):
        files = render_manifests(partition)
        assert "pyproject.toml" not in files, partition
        assert not any("[project]" in body for body in files.values()), partition


def test_an_unknown_partition_is_rejected_by_name():
    with pytest.raises(ValueError, match="conda"):
        render_manifests("conda")


def test_a_partition_with_no_rendering_is_rejected_rather_than_given_anothers():
    """The branch that catches a name added to PARTITIONS and nowhere else.

    Without it the final branch would answer for any unrecognised name, so a new
    partition would be built from another partition's manifest and the run would
    report that format as exercised.
    """
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(python_fixture_spec, "PARTITIONS", (*PARTITIONS, "pdm"))
        with pytest.raises(ValueError, match="no manifest rendering"):
            render_manifests("pdm")


def test_every_toml_manifest_parses_as_toml():
    """A manifest is TOML before it is anything else.

    The renderers build these by string concatenation, so an unquoted value or a
    lost newline produces a file that reads correctly and that no manager can
    load. Parsing here is what stops that reaching a fixture tree, where it would
    surface as the manager failing and be read as a missing tool.

    Selected by shape rather than by a list of filenames, so a renderer that
    later emits `uv.toml` or `poetry.toml` is parsed too instead of silently
    escaping the check, and counted so that the whole test cannot pass by
    parsing nothing.
    """
    parsed = 0
    for partition in PARTITIONS:
        for name, body in render_manifests(partition).items():
            if name.endswith(".toml") or name == "Pipfile":
                tomllib.loads(body)
                parsed += 1
    assert parsed >= len(PARTITIONS) - 1, parsed


def test_every_declared_dependency_reaches_every_partition_at_its_pin():
    """Name and pin have to meet on one line, not merely both be present.

    Searching the concatenated bodies cannot tell a correct rendering from one
    with two pins swapped between packages: both names and both pins are still
    somewhere in the text. The round rests on the exact pins - jinja2 3.1.2 is
    what makes the vulnerability seed real - so the pairing is the property.
    """
    for partition in PARTITIONS:
        lines = "".join(render_manifests(partition).values()).splitlines()
        for dependency in declared():
            assert any(
                dependency.name in line and dependency.pin in line for line in lines
            ), (partition, dependency.name, dependency.pin)


def test_each_partition_declares_the_set_in_exactly_one_file():
    """Two files declaring the same set is how a partition stops being one.

    Each tool reads whichever manifest it prefers, so a partition whose format
    is never the one read still produces a full result and the run records the
    lens as exercised. The build manifest the `pip` and `pipenv` partitions need
    for their src-layout install therefore has to declare nothing.

    The carrier is found by dependency *name*, not by pin: an unpinned
    `install_requires=["jinja2"]` added to the build manifest declares the set a
    second time while carrying no pin at all, so a pin-based search would report
    one carrier and miss it.
    """
    for partition in PARTITIONS:
        files = render_manifests(partition)
        for dependency in declared():
            pattern = rf"(?i)(?<![\w.-]){re.escape(dependency.name)}(?![\w.-])"
            carriers = [n for n, body in files.items() if re.search(pattern, body)]
            assert len(carriers) == 1, (partition, dependency.name, carriers)


def test_every_partition_renders_exactly_one_build_manifest():
    """The src-layout package has to be installable in every partition.

    Running the seeded suite against a tree where only the dependencies were
    installed fails at collection with `ModuleNotFoundError: No module named
    'fixture_app'`, which is indistinguishable from a broken fixture. So every
    partition renders exactly one build manifest: a `pyproject.toml` carrying a
    build backend where the format allows it, and a `setup.py` where declaring
    the dependency set in `pyproject.toml` would take the partition's own format
    out of play.
    """
    for partition in PARTITIONS:
        files = render_manifests(partition)
        build_manifests = [n for n in files if n in ("pyproject.toml", "setup.py")]
        assert len(build_manifests) == 1, (partition, build_manifests)
        body = files[build_manifests[0]]
        assert "build-system" in body or "setuptools" in body, partition


def test_every_partition_states_the_interpreter_floor():
    """Each format spells the floor its own way, so the constant is the anchor.

    Interpolating `PYTHON_FLOOR` is what keeps the spellings from disagreeing;
    this fails if a renderer is written with the number typed in instead and the
    constant is later moved.
    """
    for partition in PARTITIONS:
        bodies = "".join(render_manifests(partition).values())
        assert python_fixture_spec.PYTHON_FLOOR in bodies, partition


def test_every_expectation_names_a_known_partition_and_form():
    """Every field an expectation is read through has to carry something.

    A subset assertion on `partitions` passes for the empty tuple, which is an
    expectation no partition ever runs - it renders into the published record
    and satisfies the seed-coverage union while guarding nothing. So emptiness
    is rejected here for each of the three fields a reader acts on.
    """
    for expectation in EXPECTATIONS:
        assert expectation.partitions, expectation.check
        assert set(expectation.partitions) <= set(PARTITIONS), expectation.check
        assert expectation.form in FORMS, expectation.check
        assert expectation.claim.strip(), expectation.check


def test_every_expectation_names_a_check_record_carrying_python_tooling():
    """A check id is only meaningful if a record answers to it.

    Nothing else in this module can tell `deps/hygeine` from `deps/hygiene`:
    the typo renders into the published table, the harness looks for a record
    that is not there, and the run reports a check that does not exist. The
    Python-tooling half matters too - an expectation against a record with no
    Python lens states a result no partition here could produce.
    """
    records = _python_lens_records()
    for expectation in EXPECTATIONS:
        assert expectation.check in records, expectation.check


def test_every_python_lens_record_is_expected_on_the_full_partition():
    """The claim `FULL_PARTITION` is named for, held against the records.

    Whichever partition `FULL_PARTITION` names carries every `python:` entry in
    the family. Set equality is what makes that falsifiable in both directions:
    a new record with a Python lens and no expectation fails here rather than
    being silently left out of the round, and an expectation scoped away from
    the full partition by accident fails too. The assertion is symmetric under
    moving `FULL_PARTITION`, so it holds the coverage claim rather than the
    identity of the partition - which the next test pins, because the published
    record and PR 2's harness both name that partition directly.
    """
    on_full = {e.check for e in expectations_for(FULL_PARTITION)}
    assert on_full == _python_lens_records()


def test_the_full_partition_is_the_one_that_can_build_every_other():
    """`FULL_PARTITION` is pinned, not merely referenced.

    Every other assertion here is written relative to it and so stays green
    wherever it points. But uv is how the whole fixture set is built - it
    resolves the tree, exports the requirements and PEP 751 partitions directly,
    and runs the poetry and pipenv lock steps as one-shot commands - so moving
    this would leave the partition that has to answer every check unable to
    build the fixtures the rest of the round depends on.
    """
    assert FULL_PARTITION == "uv"
    assert FULL_PARTITION in PARTITIONS


def test_the_full_partition_carries_every_check_any_partition_carries():
    """The same claim read from the module alone rather than from the records.

    A comparison of lengths - the full partition carries more expectations than
    a thin one - is satisfied by a check scoped to the thin partitions only,
    which is the mistake worth catching: the full partition would then not be
    the superset the record and the renderer both describe.
    """
    assert {e.check for e in expectations_for(FULL_PARTITION)} == {
        e.check for e in EXPECTATIONS
    }


def test_no_check_states_two_expectations_for_one_partition():
    """Two expectations for one (check, partition) pair are a contradiction.

    Both would apply, `expectations_for` would return both, and the run would
    have two different right answers for one observation. Every set-valued
    assertion in this file is blind to it, because a duplicate collapses into
    the set. This is the guard that lets the scoped pairs - `deps/hygiene` and
    `deps/inventory`, each split in two - be read as a partition of PARTITIONS
    rather than merely a cover of it.
    """
    seen: set[tuple[str, str]] = set()
    for expectation in EXPECTATIONS:
        for partition in expectation.partitions:
            assert (expectation.check, partition) not in seen, (
                expectation.check,
                partition,
            )
            seen.add((expectation.check, partition))


def test_every_planted_seed_is_expected_and_every_expected_seed_is_planted():
    """Both seed sources and both directions.

    Five of the six dependency seeds never appear in SOURCE_FILES, so unioning
    only the tree would leave `vulnerable`, `stale`, `copyleft`,
    `transitive-root` and `declared-unused` unguarded - which is most of what
    the deps half of the round is for.

    The reverse direction catches a misspelled seed on an expectation. Spelling
    `cycle` as `cylce` on `arch/cycles` leaves the forward direction satisfied,
    because `arch/coupling` names `cycle` too, so the seed still looks covered
    while the expectation that was meant to carry it no longer does.
    """
    planted = {s for f in SOURCE_FILES for s in f.seeds} | {
        s for d in DEPENDENCIES for s in d.seeds
    }
    expected = {s for e in EXPECTATIONS for s in e.seeds}
    assert planted - expected == set()
    assert expected - planted == set()


def test_the_deps_checks_are_exactly_the_deps_domain_of_the_expectations():
    """DEPS_CHECKS is a view of EXPECTATIONS, not a second list of its own.

    The harness and the thin-partition scoping both read it, so a `deps` record
    gaining an expectation and not a DEPS_CHECKS entry would leave the thin
    partitions running a check nothing says they carry.
    """
    assert set(DEPS_CHECKS) == {
        e.check for e in EXPECTATIONS if e.check.startswith("deps/")
    }


def test_the_deps_checks_are_expected_on_every_partition():
    """Every deps check has a stated expectation on all five partitions.

    Scoping splits a check across two expectations - `deps/hygiene` says one
    thing on `pipenv` and another everywhere else - so the property is over the
    union rather than over any single entry. Equality rather than containment,
    with the no-duplicate guard above, makes the two entries a partition of
    PARTITIONS: no partition left without an answer, none given two.
    """
    for check in DEPS_CHECKS:
        matching = [e for e in EXPECTATIONS if e.check == check]
        assert matching, check
        assert {p for e in matching for p in e.partitions} == set(PARTITIONS), check


def test_the_thin_partitions_carry_the_deps_checks_and_coverage_only():
    """All four thin partitions, derived rather than named.

    Asserting this of `poetry` alone would pass while `pipenv` carried the
    wrong set, and `pipenv` is the partition whose `deps/hygiene` expectation
    is the scoped one - the entry most likely to be scoped wrongly.
    """
    for partition in set(PARTITIONS) - {FULL_PARTITION}:
        carried = {e.check for e in expectations_for(partition)}
        assert carried == set(DEPS_CHECKS) | {THIN_EXTRA_CHECK}, partition


def test_expectations_for_rejects_an_unknown_partition_by_name():
    with pytest.raises(ValueError, match="conda"):
        expectations_for("conda")


def test_scoping_away_a_name_that_is_not_a_partition_is_rejected():
    """The helper that writes the scoped tuples fails loudly on a typo.

    `_partitions_except("pipnev")` would otherwise return all five partitions,
    which is the opposite of what the caller asked for, and the expectation
    would silently claim the very partition it was written to exclude.
    """
    with pytest.raises(ValueError, match="pdm"):
        python_fixture_spec._partitions_except("pdm")


def test_the_vulnerability_expectation_is_a_floor_naming_every_verified_cve():
    """The CVE list lives in two places, so it can disagree with itself.

    `jinja2`'s `evidence` records what OSV returned; the expectation's `claim`
    is what PR 2 checks the tool against. Re-verifying the pin updates the
    first, and nothing but this makes it update the second - a claim short of a
    CVE the evidence names would pass a tool that missed it.
    """
    expectation = next(e for e in EXPECTATIONS if e.check == "deps/vulnerabilities")
    assert expectation.form == "floor"
    evidenced = set(
        re.findall(r"CVE-\d{4}-\d+", "".join(d.evidence for d in DEPENDENCIES))
    )
    assert evidenced, "no CVE is recorded in any dependency's evidence"
    assert evidenced <= set(re.findall(r"CVE-\d{4}-\d+", expectation.claim))


def test_the_docstring_expectation_names_the_seeded_file_and_admits_the_others():
    """The seed is one file; the tool's output is seven.

    The three empty `__init__.py` files and three of the seeded tests carry no
    module docstring either, so a per-file report names them alongside
    `unsafe.py`. An expectation naming `unsafe.py` as the only docstring-less
    file in the fixture would make correct output look like over-reporting.
    """
    without = [f.path for f in SOURCE_FILES if not f.body.startswith('"""')]
    assert [p for p in without if p.startswith("src/") and "__init__" not in p] == [
        f"src/{PACKAGE}/unsafe.py"
    ]
    assert set(python_fixture_spec._FILES_WITHOUT_MODULE_DOCSTRING) == set(without)
    tree = source_tree()
    for path in python_fixture_spec._FILES_WITHOUT_MODULE_DOCSTRING:
        assert path in tree, path
    expectation = next(e for e in EXPECTATIONS if e.check == "docs/docstring-coverage")
    assert str(len(without)) in expectation.claim


def test_the_isolation_expectation_carries_both_measured_durations():
    """The sleep and the timeout are one fact, and the claim states both.

    Naming the constants without their values leaves a reader of the published
    record unable to tell whether the sleep still exceeds the timeout, which is
    the only thing the seed depends on.
    """
    expectation = next(e for e in EXPECTATIONS if e.check == "test/isolation")
    assert python_fixture_spec.SLOW_TEST_SECONDS > (
        python_fixture_spec.ISOLATION_TIMEOUT_SECONDS
    )
    assert f"{python_fixture_spec.SLOW_TEST_SECONDS}s" in expectation.claim
    assert f"{python_fixture_spec.ISOLATION_TIMEOUT_SECONDS}s" in expectation.claim


def test_every_identifier_a_claim_names_resolves_in_the_seeded_tree():
    """A claim may only name code the fixture actually writes.

    The module's promise is that the tree and the expectations come from one
    definition, and for the seed vocabulary and the measured numbers it keeps
    that promise by construction. Identifiers were the hole: renaming a seeded
    function, or replacing the call a check is planted to catch, left every
    claim naming it untouched and the suite green - which is the "reads exactly
    like a tool that correctly found nothing" failure arriving from the other
    side, since here the expectation survives and the seed is what went missing.
    """
    tree = source_tree()
    for expectation in EXPECTATIONS:
        for text in (expectation.claim, expectation.ungranted):
            for path, selector in _TEST_REF.findall(text):
                assert path in tree, (expectation.check, path)
                if selector:
                    assert f"def {selector}" in tree[path], (
                        expectation.check,
                        selector,
                    )
            for dotted in _DOTTED_NAME.findall(text):
                parts = dotted.split(".")
                module = "src/" + "/".join(parts) + ".py"
                if module in tree:
                    continue
                module = "src/" + "/".join(parts[:-1]) + ".py"
                assert module in tree, (expectation.check, dotted)
                assert f"def {parts[-1]}" in tree[module], (expectation.check, dotted)


def test_every_planted_seed_is_classified_as_a_construct_or_as_an_absence():
    """A new seed has to be classified, not default into being unguarded.

    `SEED_MARKERS` and `ABSENCE_SEEDS` must partition every seed the tree
    plants. Held as a partition rather than as two independent subsets because
    a seed missing from both would simply go unmarked, which is exactly the
    silence the marker mapping exists to remove.
    """
    planted = {seed for f in SOURCE_FILES for seed in f.seeds}
    classified = set(python_fixture_spec.SEED_MARKERS) | set(
        python_fixture_spec.ABSENCE_SEEDS
    )
    assert planted == classified
    assert not set(python_fixture_spec.SEED_MARKERS) & set(
        python_fixture_spec.ABSENCE_SEEDS
    )


def test_every_marked_seed_still_has_its_construct_in_the_seeded_source():
    """The construct, not just the name, has to survive.

    Deleting the `eval` from `run_expression` leaves the module, the function,
    the seed list and every claim naming it untouched. Only this reads the body
    and notices the finding is no longer planted.
    """
    for seed, markers in python_fixture_spec.SEED_MARKERS.items():
        bodies = [f.body for f in SOURCE_FILES if seed in f.seeds]
        assert bodies, seed
        for marker in markers:
            assert any(marker in body for body in bodies), (seed, marker)


def test_the_complexity_seed_uses_no_conditional_expression():
    """Ruff does not walk a ternary, and radon does.

    A seed leaning on one measures lower in ruff than in radon, and C901 fires
    on `>` rather than `>=` - so a branch rewritten as `x if c else y` can drop
    the function to exactly ruff's default, where it passes in silence while
    radon still reports it over. Nothing else in the suite would notice.
    """
    body = python_fixture_spec._COMPLEXITY
    assert not re.search(r"=.+ if .+ else ", body), body
    branches = len(re.findall(r"\b(?:if|elif)\b", body))
    assert branches >= 10, branches


def test_the_ungranted_answer_is_stated_exactly_where_the_grant_changes_it():
    """The second axis is derived from the records, never judged per entry.

    A check answers something different without the grant when the Python
    tools it offers all carry a `needs` tier and something still answers once
    the grant is withheld. Where nothing does, the ungranted answer is
    `no-evidence (not-permitted)` and restating it here would add a copy to
    keep in step; where some Python tool needs no grant, `claim` already holds
    in both states. Deriving the requirement rather than eyeballing it is what
    stops a new expectation quietly omitting the axis.

    **Both halves read the schema the record declares, and neither is
    schema-neutral.** A record declaring `tooling:` states what still answers
    in `ungranted_note` and has only one place to carry a tier, which is per
    tool. A record declaring `routes:` states it by keeping an untiered
    answering route, and carries a tier per route.

    The tiered half is what reads per route, and the reason is that
    `_project_needs` collapses routes onto tools. A tool with one tiered route
    and one untiered route reads through the projected pair as tiered, so the
    record's whole language does too, and the derivation then demands an
    ungranted claim from a check whose default route is untiered and answers
    the same either way. `deps/inventory` is that shape. Reading it per route
    through `_languages_whose_tools_all_need_a_grant` asks the question the
    projection cannot: whether any route *naming a tool* still answers.

    The two halves are deliberately over different sets, and collapsing them
    breaks this test rather than simplifying it. Asking whether every
    answering route is tiered would be the exact complement of the third
    condition, since `_routes_answering_ungranted` returns precisely the
    untiered answering routes - `differs` would be unsatisfiable and every
    expectation carrying a measured `ungranted` claim would lose it. What
    distinguishes the records that need the claim is that their untiered
    escape names no tool: `deps/freshness` has `uv` and `pip` both tiered and
    a registry-comparison route that needs no grant and names nothing, so it
    projects no tool at all and the pair is the one place that answer is
    invisible.
    """
    checks, errors = load_checks(SKILLS_DIR)
    assert not errors, errors
    for expectation in EXPECTATIONS:
        record = checks[expectation.check]
        if record.routes:
            tooling_needs_a_grant = "python" in _languages_whose_tools_all_need_a_grant(
                record.routes
            )
            answers = bool(_routes_answering_ungranted(record.routes).get("python", ()))
        else:
            python_tools = set(record.tooling.get("python", ()))
            tiered = {t for names in (record.needs or {}).values() for t in names}
            tooling_needs_a_grant = bool(python_tools) and python_tools <= tiered
            answers = (record.ungranted_note or "").strip() not in ("", "none")
        differs = tooling_needs_a_grant and answers
        assert bool(expectation.ungranted) == differs, (expectation.check, differs)


def test_the_ungranted_axis_is_not_vacuous():
    """The test above passes on a tree where no expectation states the axis.

    It holds `bool(expectation.ungranted) == differs`, so a derivation that
    stopped finding any check whose answer changes would fail loudly - unless
    the claims were deleted in the same breath, which moves both sides
    together and leaves it green. That is the shape this floor exists for, and
    it is the same argument `test_the_classification_is_not_vacuous` makes
    about `needs:`.

    The floor is the number of expectations carrying the axis today, with no
    slack, because each of those claims was graded against an actual
    `--grant none` run and an unmeasured one reads exactly like a measured
    one. If this fails, a claim was removed - restore it rather than lowering
    the floor.
    """
    stated = sorted((e.check, e.partitions) for e in EXPECTATIONS if e.ungranted)
    assert len(stated) >= 8, f"only {len(stated)} expectation(s) state it: {stated}"


def test_the_over_decomposition_expectation_carries_the_computed_file_count():
    """The count in that claim has to move when the tree does.

    Its own prose says the package is a given number of files under `src/`, and
    a typed-in number stops being that claim the first time a seed is added -
    the published record would then state a size the fixture no longer has.
    """
    counted = len([f for f in SOURCE_FILES if f.path.startswith(f"src/{PACKAGE}/")])
    assert counted == python_fixture_spec._SRC_FILE_COUNT
    expectation = next(e for e in EXPECTATIONS if e.check == "arch/over-decomposition")
    assert str(counted) in expectation.claim


def test_the_self_import_row_count_matches_the_files_that_self_import():
    """deptry emits one DEP003 per src file importing the package by name."""
    counted = [
        f.path
        for f in SOURCE_FILES
        if f.path.startswith(f"src/{PACKAGE}/") and f"import {PACKAGE}" in f.body
    ]
    assert set(counted) == set(python_fixture_spec._SRC_FILES_IMPORTING_PACKAGE)
    expectation = next(
        e
        for e in EXPECTATIONS
        if e.check == "deps/hygiene" and "pipenv" not in e.partitions
    )
    assert str(len(counted)) in expectation.claim


def test_an_expectation_with_an_unknown_form_is_rejected_by_name():
    """`form` drives how PR 2 grades the observation, so a typo cannot pass."""
    with pytest.raises(ValueError, match="approximately"):
        python_fixture_spec.Expectation(
            "arch/cycles", (FULL_PARTITION,), "approximately", "claim", ()
        )


def test_an_expectation_scoped_to_an_unknown_partition_is_rejected_by_name():
    """A partition typo would scope an entry to nothing and read as covered."""
    with pytest.raises(ValueError, match="pdm"):
        python_fixture_spec.Expectation("arch/cycles", ("pdm",), "exact", "claim", ())


_EXPECTATION_HEADER = "| Check | Partitions | Form | Seeds | Expected |"
_UNGRANTED_HEADER = "| Check | Partitions | Without the grant |"
_DEPENDENCY_HEADER = "| Package | Pin | Imported | Seeds | Evidence |"
_PARTITION_HEADER = "| Partition | Expectations | Checks |"


def test_the_rendered_record_names_every_expectation():
    text = _load_renderer().render()
    for expectation in EXPECTATIONS:
        assert expectation.check in text, expectation.check
        assert expectation.claim.split(".")[0][:40] in text, expectation.check


def test_the_expectation_table_has_one_row_per_expectation_not_per_check():
    """The row count is the guard against a renderer keyed on the check id.

    Two checks state a different answer per partition and so carry several
    entries each; a renderer that iterated checks would drop all but one of them
    and the published record would state an answer for a partition that is not
    the one it runs on. Every set-valued and substring assertion here is blind
    to that, because the surviving entry still names the check.
    """
    rows = _table_rows(_load_renderer().render(), _EXPECTATION_HEADER)
    assert len(rows) == len(EXPECTATIONS)
    assert len(EXPECTATIONS) > len({e.check for e in EXPECTATIONS}), (
        "no check carries more than one entry, so this guards nothing"
    )


def test_the_rendered_record_carries_the_verified_evidence_per_dependency():
    text = _load_renderer().render()
    for dependency in DEPENDENCIES:
        assert dependency.name in text, dependency.name
        assert dependency.evidence[:30] in text, dependency.name


def test_the_rendered_record_dates_the_evidence():
    """The evidence is only worth its date, so the date has to reach the page."""
    assert VERIFIED_ON in _load_renderer().render()


def test_the_grant_section_has_one_row_per_entry_whose_answer_the_grant_moves():
    """Scoped entries again: `deps/hygiene` carries two, one per scope.

    A grant section keyed on the check id would publish one of them and read as
    complete, which is the failure this axis exists to prevent - graded against
    the wrong answer, a correct ungranted run is recorded as a tool defect.
    """
    text = _load_renderer().render()
    carrying = [e for e in EXPECTATIONS if e.ungranted]
    rows = _table_rows(text, _UNGRANTED_HEADER)
    assert len(rows) == len(carrying)
    assert f"{len(carrying)} of the {len(EXPECTATIONS)} entries" in text
    for expectation in carrying:
        assert expectation.ungranted.split(".")[0][:40] in text, expectation.check


def test_the_rendered_record_states_no_count_the_module_does_not_produce():
    """Every count on the page is interpolated, so each has to be the real one."""
    text = _load_renderer().render()
    for partition in PARTITIONS:
        assert f"| `{partition}` | {len(expectations_for(partition))} |" in text, (
            partition
        )
    assert f"{len(EXPECTATIONS)} entries over " in text


def test_the_rendered_record_uses_no_em_dash():
    """Both generated neighbours in docs/audit carry none, and this joins them."""
    assert "—" not in _load_renderer().render()


def test_the_rendered_record_ends_with_exactly_one_newline():
    text = _load_renderer().render()
    assert text.endswith("\n")
    assert not text.endswith("\n\n")


def test_every_table_cell_survives_being_a_table_cell():
    """A newline ends a GFM row and a bare pipe opens a column.

    `--check` is no safety net: it compares a fresh render against the committed
    one, and both would carry the same broken table. So every table is held to
    the column count its header declares - all four, because the cell that was
    left unescaped was a dependency `pin`, in the one table an earlier version
    of this test did not cover, and real tool output carries pipes: the
    `deps/inventory` poetry claim already contains one.
    """
    text = _load_renderer().render()
    for header in (
        _EXPECTATION_HEADER,
        _UNGRANTED_HEADER,
        _DEPENDENCY_HEADER,
        _PARTITION_HEADER,
    ):
        columns = header.count("|")
        rows = _table_rows(text, header)
        assert rows, header
        for row in rows:
            assert row.replace("\\|", "").count("|") == columns, row


def _cells(row: str) -> list[str]:
    """The cells of a rendered GFM row, outer pipes dropped.

    Split on unescaped pipes only. A claim that legitimately contains one -
    `deps/inventory` on poetry quotes cyclonedx-py's `CRITICAL | CDX` banner -
    reaches the cell as `\\|`, and splitting on that would shred a correct row
    into extra columns and fail the pairing test on output that is right.
    """
    return [c.strip() for c in re.split(r"(?<!\\)\|", row.strip().strip("|"))]


def test_every_expectation_row_pairs_its_check_with_its_own_answer():
    """The row count and the substring searches are both blind to a mispairing.

    Pairing each row's check id with a neighbouring entry's scope and claim
    leaves the row count right, every check id present and every claim present,
    so a record stating one scope's answer under another scope's check passes
    every other assertion here. That is the failure the per-expectation
    rendering exists to prevent, and until this test the design prevented one
    route to it while nothing checked the result.

    Located by check id *and* scope together, because the two multi-entry checks
    are precisely where a mispairing can hide.
    """
    renderer = _load_renderer()
    rows = [_cells(r) for r in _table_rows(renderer.render(), _EXPECTATION_HEADER)]
    for expectation in EXPECTATIONS:
        wanted_scope = renderer._partitions_cell(expectation)
        matching = [
            r for r in rows if r[0] == f"`{expectation.check}`" and r[1] == wanted_scope
        ]
        assert len(matching) == 1, (expectation.check, wanted_scope)
        _, _, form, seeds, claim = matching[0]
        assert form == expectation.form, expectation.check
        assert seeds == renderer._seeds_cell(expectation), expectation.check
        assert claim == renderer._cell(expectation.claim), expectation.check


def test_every_grant_row_pairs_its_check_with_its_own_ungranted_answer():
    """`deps/hygiene` carries two, and they say opposite things.

    One reports the undeclared import as DEP003 and the other cannot read the
    manifest format at all, so a swap between them publishes a confident wrong
    answer that every count and substring assertion accepts.
    """
    renderer = _load_renderer()
    rows = [_cells(r) for r in _table_rows(renderer.render(), _UNGRANTED_HEADER)]
    for expectation in (e for e in EXPECTATIONS if e.ungranted):
        wanted_scope = renderer._partitions_cell(expectation)
        matching = [
            r for r in rows if r[0] == f"`{expectation.check}`" and r[1] == wanted_scope
        ]
        assert len(matching) == 1, (expectation.check, wanted_scope)
        assert matching[0][2] == renderer._cell(expectation.ungranted), (
            expectation.check
        )


def test_every_partition_row_states_its_own_expectation_count_and_check_set():
    """The Checks column was free to say anything.

    Replacing it wholesale with a literal left the suite green, because the only
    assertion over this table was that the count column matched. The cell is
    what tells a reader which partition answers which check, so it is the half
    that carries the meaning.
    """
    renderer = _load_renderer()
    rows = [_cells(r) for r in _table_rows(renderer.render(), _PARTITION_HEADER)]
    assert len(rows) == len(PARTITIONS)
    for partition in PARTITIONS:
        matching = [r for r in rows if r[0] == f"`{partition}`"]
        assert len(matching) == 1, partition
        _, count, checks = matching[0]
        assert count == str(len(expectations_for(partition))), partition
        assert checks == renderer._partition_checks_cell(partition), partition


def test_every_dependency_row_pairs_its_package_with_its_own_pin_and_evidence():
    """The dependency table's four non-name columns were unasserted.

    Truncating every evidence string, or flipping every `Imported` cell, left
    the suite green: the only assertions were that the name appears somewhere on
    the page and that the first 30 characters of the evidence do.
    """
    renderer = _load_renderer()
    rows = [_cells(r) for r in _table_rows(renderer.render(), _DEPENDENCY_HEADER)]
    assert len(rows) == len(DEPENDENCIES)
    for dependency in DEPENDENCIES:
        matching = [r for r in rows if r[0] == f"`{renderer._cell(dependency.name)}`"]
        assert len(matching) == 1, dependency.name
        _, pin, imported, seeds, evidence = matching[0]
        expected_pin = (
            f"`{renderer._cell(dependency.pin)}`"
            if dependency.pin
            else "*(undeclared)*"
        )
        assert pin == expected_pin, dependency.name
        assert imported == ("yes" if dependency.imported else "no"), dependency.name
        assert seeds == renderer._cell(", ".join(dependency.seeds)), dependency.name
        assert evidence == renderer._cell(dependency.evidence), dependency.name


def test_the_committed_record_matches_the_module():
    assert _RECORD.read_text() == _load_renderer().render()


def test_check_exits_zero_and_says_nothing_when_the_record_is_current(capsys):
    assert _load_renderer().main(["--check"]) == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_check_exits_one_with_a_diff_when_the_record_has_drifted(
    tmp_path, monkeypatch, capsys
):
    """The gate has to be able to fail, which a passing gate cannot show.

    A `--check` that always returned 0 would look exactly like a record that is
    always current, and CI would wave through a spec edit that was never
    re-rendered.
    """
    renderer = _load_renderer()
    stale = tmp_path / "python-fixture-expectations.md"
    stale.write_text(renderer.render() + "drift\n")
    monkeypatch.setattr(renderer, "OUT_PATH", stale)
    assert renderer.main(["--check"]) == 1
    assert "drift" in capsys.readouterr().err


def test_check_treats_a_missing_record_as_drift(tmp_path, monkeypatch, capsys):
    renderer = _load_renderer()
    monkeypatch.setattr(renderer, "OUT_PATH", tmp_path / "absent.md")
    assert renderer.main(["--check"]) == 1
    assert capsys.readouterr().err


def test_rendering_without_check_writes_the_record(tmp_path, monkeypatch, capsys):
    renderer = _load_renderer()
    out = tmp_path / "python-fixture-expectations.md"
    monkeypatch.setattr(renderer, "OUT_PATH", out)
    assert renderer.main([]) == 0
    assert out.read_text() == renderer.render()
    assert "wrote" in capsys.readouterr().out
