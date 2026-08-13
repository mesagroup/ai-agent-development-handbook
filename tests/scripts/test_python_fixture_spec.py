"""Tests for scripts/python_fixture_spec.py (#45)."""

import re
import tomllib

import pytest
import python_fixture_spec
from audit_checks import SKILLS_DIR, load_checks
from python_fixture_spec import (
    DEPENDENCIES,
    DEPS_CHECKS,
    EXPECTATIONS,
    FULL_PARTITION,
    PARTITIONS,
    SOURCE_FILES,
    THIN_EXTRA_CHECK,
    declared,
    expectations_for,
    render_manifests,
    source_tree,
)


def _python_lens_records() -> set[str]:
    """Every check record in the family that names a Python tool.

    Read from the records rather than listed here: the fixture round exists to
    exercise the `python:` tooling entries, so the set it must cover is whatever
    the family currently declares, not a copy of it taken when this was written.
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
        assert expectation.form in ("exact", "floor", "absence"), expectation.check
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

    `uv` carries every `python:` entry in the family. Set equality is what makes
    that falsifiable in both directions: a new record with a Python lens and no
    expectation fails here rather than being silently left out of the round, and
    an expectation scoped away from the full partition by accident fails too.
    """
    on_full = {e.check for e in expectations_for(FULL_PARTITION)}
    assert on_full == _python_lens_records()


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
        f"src/{python_fixture_spec.PACKAGE}/unsafe.py"
    ]
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
    assert str(python_fixture_spec.SLOW_TEST_SECONDS) in expectation.claim
    assert str(python_fixture_spec.ISOLATION_TIMEOUT_SECONDS) in expectation.claim
