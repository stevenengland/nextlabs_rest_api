from __future__ import annotations

from nextlabs_sdk._cli._diff._engine import diff_payloads


def test_reordered_idless_array_yields_no_change():
    """Given two payloads whose only difference is tag ordering.

    When diffing.
    Then there are no changes.
    """
    old = {"name": "P", "tags": [{"key": "a"}, {"key": "b"}]}
    new = {"name": "P", "tags": [{"key": "b"}, {"key": "a"}]}

    result = diff_payloads(old, new)

    assert result.changes == ()


def test_deployment_noise_excluded_by_default():
    """Given payloads differing only in deployment-noise leaf fields.

    When diffing without show_all.
    Then no visible changes, but the hidden count reflects the noise.
    """
    old = {"name": "P", "deploymentTime": 1, "createdDate": 10, "modifiedBy": "x"}
    new = {"name": "P", "deploymentTime": 2, "createdDate": 20, "modifiedBy": "y"}

    result = diff_payloads(old, new)

    assert result.changes == ()
    assert result.hidden_noise_count == 3


def test_version_change_stays_visible():
    """Given payloads differing only in version.

    When diffing.
    Then the version change is reported.
    """
    old = {"name": "P", "version": 3}
    new = {"name": "P", "version": 4}

    result = diff_payloads(old, new)

    assert any(c.path == ("version",) and c.kind == "change" for c in result.changes)


def test_nested_scalar_change_recorded_with_path():
    """Given a nested scalar edit.

    When diffing.
    Then the change carries the full nested path.
    """
    old = {"environmentConfig": {"remoteAccess": 1}}
    new = {"environmentConfig": {"remoteAccess": 2}}

    result = diff_payloads(old, new)

    assert any(
        c.path == ("environmentConfig", "remoteAccess") and c.old == 1 and c.new == 2
        for c in result.changes
    )


def test_show_all_reincludes_noise_and_ordering():
    """Given payloads differing in noise and array order.

    When diffing with show_all.
    Then the deployment noise difference is now visible.
    """
    old = {"deploymentTime": 1, "tags": [{"key": "a"}, {"key": "b"}]}
    new = {"deploymentTime": 2, "tags": [{"key": "b"}, {"key": "a"}]}

    result = diff_payloads(old, new, show_all=True)

    assert any(c.path == ("deploymentTime",) for c in result.changes)
