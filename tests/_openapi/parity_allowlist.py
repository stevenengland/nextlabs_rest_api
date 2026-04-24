"""Known drift between the SDK and the vendor OpenAPI spec.

Each entry is an explicit opt-out for the parity checks in
:mod:`tests._openapi.model_parity`. Removing an entry is the signal
that the drift has been fixed (upstream or in the SDK) and the test
layer should once again enforce the parity.

Reasons are documented inline as comments on each tuple so future
maintainers can judge whether the opt-out still applies. Reasons
cluster into:

* **SDK stricter than spec** — the SDK pragmatically treats a field as
  required even though the vendor OpenAPI leaves it optional (usually
  because every real response carries it).
* **Spec incomplete** — the vendor OpenAPI omits ``required`` entirely
  or the inner ``*DTORes`` schema for this endpoint.
* **SDK gap** — the SDK does not yet expose a field/enum value the
  spec documents; follow-up work.

The first element of every tuple is the SDK model's class name so
entries stay stable across file moves.
"""

from __future__ import annotations


# (model_name, field_alias) — SDK requires, spec does not.
REQUIRED_ONLY_IN_SDK: frozenset[tuple[str, str]] = frozenset(
    (
        # SDK stricter — every real response carries these keys.
        ("Component", "id"),
        ("Component", "type"),
        ("Policy", "id"),
        # Spec omits ``required`` entirely for these DTOs.
        ("ComponentType", "id"),
        ("ComponentType", "name"),
        ("ComponentType", "shortName"),
        ("ComponentType", "type"),
        ("ComponentType", "status"),
        ("DeploymentResult", "id"),
        # Spec has no inner schema for dependencies — SDK's pragmatic
        # required-set would otherwise fail parity against an empty
        # schema. Kept here for completeness in case the NO_INNER_SCHEMA
        # skip is ever narrowed.
        ("Dependency", "id"),
        ("Dependency", "type"),
        ("Dependency", "name"),
    ),
)


# (model_name, field_alias) — spec requires, SDK does not.
REQUIRED_ONLY_IN_SPEC: frozenset[tuple[str, str]] = frozenset()


# (model_name, field_alias) — SDK exposes, spec does not document.
PROPERTY_ONLY_IN_SDK: frozenset[tuple[str, str]] = frozenset(
    (
        # Audit-observed ownership / audit / index-control fields that
        # the vendor ``*DTORes`` schemas omit but real responses do
        # include.
        ("Component", "hidden"),
        ("Component", "modifiedBy"),
        ("Component", "modifiedById"),
        ("Component", "ownerDisplayName"),
        ("Component", "ownerId"),
        ("Component", "preCreated"),
        ("Component", "reIndexAllNow"),
        ("Component", "skipValidate"),
        ("Policy", "reIndexNow"),
        ("Policy", "skipAddingTrueAllowAttribute"),
        ("Policy", "skipValidate"),
    ),
)


# (model_name, field_alias) — spec exposes, SDK does not model.
PROPERTY_ONLY_IN_SPEC: frozenset[tuple[str, str]] = frozenset(
    (
        # Envelope bleed-through — ``CollectionDataResponseDTO`` pagination
        # fields leaked into the ``ComponentDTORes`` schema.
        ("Component", "pageNo"),
        ("Component", "pageSize"),
        # SDK gap — ``PolicyModel.authorities`` not yet modelled.
        ("ComponentType", "authorities"),
    ),
)


# (model_name, field_alias, enum_value) — spec enum has it, SDK Enum misses it.
ENUM_ONLY_IN_SPEC: frozenset[tuple[str, str, str]] = frozenset(
    (
        # SDK gap — ``ComponentStatus`` missing ``DELETED``.
        ("Component", "status", "DELETED"),
    ),
)


# Response triples whose wrapper does not reference a typed inner DTO
# schema (e.g. ``ResponseDTO`` with only ``statusCode`` / ``message``,
# or the bare ``CollectionDataResponseDTO`` base). The parity tests
# skip these — the spec simply does not describe the inner shape.
NO_INNER_SCHEMA: frozenset[tuple[str, str, str]] = frozenset(
    (
        ("/console/api/v1/config/tags/{id}", "get", "200"),
        ("/console/api/v1/config/tags/list/{type}", "get", "200"),
        ("/console/api/v1/component/mgmt/findDependencies", "post", "200"),
        ("/console/api/v1/policy/mgmt/findDependencies", "post", "200"),
    ),
)
