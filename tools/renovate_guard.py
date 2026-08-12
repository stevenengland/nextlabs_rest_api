"""Guard the Renovate extraction report for compiled-lock ownership.

Reads the file report Renovate writes with ``--report-type=file`` and
asserts only the contract this repository needs: the ``pip-compile``
manager associates every source input with the compiled lock
``requirements/constraints.txt``.

The report is an experimental upstream interface, so parsing is narrow.
Required fields are validated, unknown fields are ignored, and the
warnings a tokenless local extraction always emits are tolerated — this
is not a general validator for Renovate configuration, workflow
versions, or rule precedence.

An override input holding nothing but comments is not extracted as a
source at all. It is accepted instead when the compiled lock's generated
header names it, which proves the compiler still reads it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

COMPILED_LOCK = "requirements/constraints.txt"
PIP_COMPILE = "pip-compile"
EXTRACTED_SOURCES = ("pyproject.toml", "requirements/dev-compile.in")
HEADER_PROVABLE_SOURCE = "requirements/overrides.in"

MISSING_TOKEN = "GitHub token is required for some dependencies"
UNEXTRACTED_SOURCE = "pip-compile: failed to find dependencies in source file"
MISSING_LOCK_ENTRY = "pip-compile: dependency not found in lock file"
TOOLCHAIN_DEPS = frozenset(("python", "setuptools"))


def _malformed(detail: str) -> str:
    return f"malformed extraction report: {detail}"


def _require_mapping(
    candidate: object, label: str, findings: list[str]
) -> dict[str, object] | None:
    """Narrow ``candidate`` to a mapping, recording a finding when it is not one."""
    if not isinstance(candidate, dict):
        findings.append(_malformed(f"{label} is not an object"))
        return None
    return candidate


def _is_documented(problem: dict[str, object]) -> bool:
    """Tell whether a report problem is a warning a local extraction always emits."""
    message = problem.get("msg")
    if message == MISSING_TOKEN:
        return True
    if message == UNEXTRACTED_SOURCE:
        return problem.get("packageFile") == HEADER_PROVABLE_SOURCE
    if message == MISSING_LOCK_ENTRY:
        dep_name = problem.get("depName")
        return dep_name is None or dep_name in TOOLCHAIN_DEPS
    return False


def _record_problems(
    section: dict[str, object], label: str, findings: list[str]
) -> None:
    """Record one finding per report problem outside the documented warnings."""
    problems = section.get("problems", [])
    if not isinstance(problems, list):
        findings.append(_malformed(f"'problems' of {label} is not a list"))
        return
    for problem in problems:
        entry = _require_mapping(problem, f"a problem of {label}", findings)
        if entry is not None and not _is_documented(entry):
            findings.append(
                f"unexpected extraction problem in {label}: {_problem_text(entry)}",
            )


def _problem_text(problem: dict[str, object]) -> str:
    """Render a problem as its message plus whatever context names it."""
    context = [
        f"{key}={problem[key]!r}"
        for key in ("depName", "packageFile", "lockFile")
        if key in problem
    ]
    message = repr(problem.get("msg"))
    if not context:
        return message
    return "{0} ({1})".format(message, ", ".join(context))


def _manager_entries(
    section: dict[str, object], name: str, findings: list[str]
) -> list[object]:
    """Return the ``pip-compile`` entries reported for one repository."""
    package_files = _require_mapping(
        section.get("packageFiles"), f"'packageFiles' of {name!r}", findings
    )
    if package_files is None:
        return []
    entries = package_files.get(PIP_COMPILE, [])
    if not isinstance(entries, list):
        findings.append(_malformed(f"'{PIP_COMPILE}' of {name!r} is not a list"))
        return []
    return entries


def _audit_repository(name: str, repository: object, findings: list[str]) -> set[str]:
    """Record one repository's problems and return its lock-owning sources."""
    label = f"repository {name!r}"
    section = _require_mapping(repository, label, findings)
    if section is None:
        return set()
    _record_problems(section, label, findings)
    owned = (
        _lock_owning_source(entry, findings)
        for entry in _manager_entries(section, name, findings)
    )
    return {source for source in owned if source is not None}


def _audit_report(report: object, findings: list[str]) -> set[str]:
    """Record every report problem and return the sources owning the compiled lock."""
    root = _require_mapping(report, "the root", findings)
    if root is None:
        return set()
    _record_problems(root, "the root", findings)
    repositories = _require_mapping(
        root.get("repositories"), "'repositories'", findings
    )
    if repositories is None:
        return set()
    owned: set[str] = set()
    for name, repository in repositories.items():
        owned |= _audit_repository(name, repository, findings)
    return owned


def _lock_owning_source(entry: object, findings: list[str]) -> str | None:
    """Return the entry's source input when the entry carries the compiled lock."""
    fields = _require_mapping(entry, f"a '{PIP_COMPILE}' entry", findings)
    if fields is None:
        return None
    source = fields.get("packageFile")
    if not isinstance(source, str):
        findings.append(
            _malformed(f"a '{PIP_COMPILE}' entry has no 'packageFile' string")
        )
        return None
    lock_files = fields.get("lockFiles", [])
    if not isinstance(lock_files, list):
        findings.append(_malformed(f"'lockFiles' of {source} is not a list"))
        return None
    return source if COMPILED_LOCK in lock_files else None


def generated_header(lock_text: str) -> str:
    """Return the compiled lock's leading comment block.

    The generated header names the compile command and its source inputs.
    Isolating it keeps a source referenced only by a ``# via`` annotation
    further down the lock from passing as a declared input.

    Args:
        lock_text: Full text of the compiled lock.

    Returns:
        The leading comment lines, joined by newlines.
    """
    header: list[str] = []
    for line in lock_text.splitlines():
        if not line.startswith("#"):
            break
        header.append(line)
    return "\n".join(header)


def check_ownership(report: object, lock_header: str) -> list[str]:
    """Return one finding per unproven source-to-lock association.

    Args:
        report: The parsed Renovate extraction report.
        lock_header: The compiled lock's generated header, which names
            the compile command's source inputs.

    Returns:
        Every finding, aggregated so one run reports the whole gap. An
        empty list means the ownership contract holds.
    """
    findings: list[str] = []
    owned = _audit_report(report, findings)

    for source in EXTRACTED_SOURCES:
        if source not in owned:
            findings.append(
                f"{source} is not associated with {COMPILED_LOCK} by the {PIP_COMPILE} manager",
            )
    if (
        HEADER_PROVABLE_SOURCE not in owned
        and HEADER_PROVABLE_SOURCE not in lock_header
    ):
        findings.append(
            f"{HEADER_PROVABLE_SOURCE} is neither an extracted source "
            f"nor an input of the {COMPILED_LOCK} generated header",
        )
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check Renovate's extraction report for compiled-lock ownership."
    )
    parser.add_argument(
        "--report", required=True, type=Path, help="path to Renovate's file report"
    )
    parser.add_argument(
        "--lock",
        type=Path,
        default=Path(COMPILED_LOCK),
        help=f"path to the compiled lock (default: {COMPILED_LOCK})",
    )
    args = parser.parse_args(argv)

    try:
        report = json.loads(args.report.read_text())
    except (OSError, ValueError) as error:
        print(
            f"could not read the extraction report {args.report}: {error}",
            file=sys.stderr,
        )
        return 1
    try:
        lock_header = generated_header(args.lock.read_text())
    except OSError as error:
        print(f"could not read the compiled lock {args.lock}: {error}", file=sys.stderr)
        return 1

    findings = check_ownership(report, lock_header)
    if not findings:
        return 0
    print(f"Renovate does not own {COMPILED_LOCK} as configured:", file=sys.stderr)
    for finding in findings:
        print(f"  - {finding}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
