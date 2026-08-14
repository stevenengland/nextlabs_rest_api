from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

import yaml

WORKFLOWS = Path(__file__).resolve().parent.parent / ".github" / "workflows"

# GitHub's own actions are deferred for now: deleting an owner from this set
# extends the invariant to it without any other edit.
FIRST_PARTY_OWNERS = frozenset(("actions",))

# The single documented exception. pypa publishes no immutable ref for its
# trusted-publishing action and recommends this branch itself; the publish jobs
# authenticate through OIDC with no long-lived token, which is what makes a
# mutable ref acceptable there. Widening this set is an intentional, reviewable
# edit — every entry carries its justification here.
PINNING_EXCEPTIONS = frozenset(("pypa/gh-action-pypi-publish@release/v1",))

COMMIT_SHA = re.compile("^[0-9a-f]{40}$")
PINNED_USES = re.compile(r"uses:\s*(?P<ref>\S+@[0-9a-f]{40})(?P<trailer>.*)$")
NON_REGISTRY_PREFIXES = ("./", "docker://")

SOME_SHA = "0123456789abcdef0123456789abcdef01234567"

UNPINNED_WORKFLOW = """
jobs:
  build:
    steps:
      - uses: some-vendor/some-action@v1
"""

ACCEPTED_WORKFLOW = f"""
jobs:
  build:
    steps:
      - uses: actions/checkout@v7
      - uses: some-vendor/some-action@{SOME_SHA}  # v1
      - uses: ./.github/actions/local-thing
      - uses: docker://alpine:3.22
"""

REUSABLE_CALL_WORKFLOW = """
jobs:
  build:
    uses: some-vendor/some-workflows/.github/workflows/build.yml@main
"""

EXCEPTED_WORKFLOW = """
jobs:
  publish:
    steps:
      - uses: pypa/gh-action-pypi-publish@release/v1
"""

UNDOCUMENTED_EXCEPTION_WORKFLOW = """
jobs:
  publish:
    steps:
      - uses: pypa/gh-action-pypi-publish@unstable
"""

UNCOMMENTED_PIN_WORKFLOW = f"""
jobs:
  build:
    steps:
      - uses: actions/checkout@{SOME_SHA}
      - uses: some-vendor/some-action@{SOME_SHA}
"""


def _uses_refs(document: str) -> list[str]:
    workflow = yaml.safe_load(document) or {}
    refs: list[str] = []
    for job in (workflow.get("jobs") or {}).values():
        called_workflow = job.get("uses")
        if called_workflow:
            refs.append(called_workflow)
        for step in job.get("steps") or ():
            step_ref = step.get("uses")
            if step_ref:
                refs.append(step_ref)
    return refs


def _is_third_party(ref: str) -> bool:
    if ref.startswith(NON_REGISTRY_PREFIXES):
        return False
    return ref.split("/")[0] not in FIRST_PARTY_OWNERS


def _is_commit_pinned(ref: str) -> bool:
    return bool(COMMIT_SHA.match(ref.rpartition("@")[-1]))


def unpinned_refs(document: str) -> list[str]:
    return [
        ref
        for ref in _uses_refs(document)
        if _is_third_party(ref)
        and ref not in PINNING_EXCEPTIONS
        and not _is_commit_pinned(ref)
    ]


# A SHA alone says nothing about which release it is, so the tag comment is the
# only thing that keeps a pinned ref reviewable. YAML parsing drops comments,
# which is why this reads the source text instead.
def uncommented_pins(document: str) -> list[str]:
    offenders: list[str] = []
    for line in document.splitlines():
        pinned = PINNED_USES.search(line)
        if pinned is None:
            continue
        ref = pinned.group("ref")
        if _is_third_party(ref) and "#" not in pinned.group("trailer"):
            offenders.append(ref)
    return offenders


def _offenders_in(
    directory: Path,
    inspect: Callable[[str], list[str]],
) -> dict[str, list[str]]:
    offenders: dict[str, list[str]] = {}
    for path in sorted(directory.glob("*.y*ml")):
        refs = inspect(path.read_text())
        if refs:
            offenders[path.name] = refs
    return offenders


def unpinned_refs_in(directory: Path) -> dict[str, list[str]]:
    return _offenders_in(directory, unpinned_refs)


def uncommented_pins_in(directory: Path) -> dict[str, list[str]]:
    return _offenders_in(directory, uncommented_pins)


def test_no_workflow_in_the_repository_runs_an_unpinned_third_party_action() -> None:
    assert unpinned_refs_in(WORKFLOWS) == {}


def test_an_unpinned_third_party_action_in_a_new_workflow_file_is_reported(
    tmp_path: Path,
) -> None:
    (tmp_path / "newly_added.yml").write_text(UNPINNED_WORKFLOW)

    assert unpinned_refs_in(tmp_path) == {
        "newly_added.yml": ["some-vendor/some-action@v1"],
    }


def test_first_party_local_and_commit_pinned_refs_are_accepted() -> None:
    assert unpinned_refs(ACCEPTED_WORKFLOW) == []


def test_a_reusable_workflow_call_is_checked_like_a_step() -> None:
    assert unpinned_refs(REUSABLE_CALL_WORKFLOW) == [
        "some-vendor/some-workflows/.github/workflows/build.yml@main",
    ]


def test_the_documented_publishing_exception_is_permitted() -> None:
    assert unpinned_refs(EXCEPTED_WORKFLOW) == []


def test_an_undocumented_ref_of_the_excepted_action_is_reported() -> None:
    assert unpinned_refs(UNDOCUMENTED_EXCEPTION_WORKFLOW) == [
        "pypa/gh-action-pypi-publish@unstable",
    ]


def test_no_pinned_third_party_action_in_the_repository_hides_its_version() -> None:
    assert uncommented_pins_in(WORKFLOWS) == {}


def test_a_pinned_third_party_action_without_a_version_comment_is_reported(
    tmp_path: Path,
) -> None:
    (tmp_path / "newly_added.yml").write_text(UNCOMMENTED_PIN_WORKFLOW)

    assert uncommented_pins_in(tmp_path) == {
        "newly_added.yml": ["some-vendor/some-action@{0}".format(SOME_SHA)],
    }


def test_a_pinned_third_party_action_with_a_version_comment_is_accepted() -> None:
    assert uncommented_pins(ACCEPTED_WORKFLOW) == []
