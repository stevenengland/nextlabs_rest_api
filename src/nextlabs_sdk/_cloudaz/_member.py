"""CloudAz composite member identity and metadata."""

from pydantic import BaseModel, ConfigDict, Field


class Member(BaseModel):
    """A member of a composite component.

    Known ``type`` values are ACTION, MEMBER, RESOURCE, and SUBJECT;
    ``status`` values are APPROVED, DELETED, and DRAFT; ``memberType``
    values are APPLICATION, HOST, HOST_GROUP, USER, and USER_GROUP.
    These fields retain other vendor values without restriction.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    id: int | None = None
    name: str | None = None
    type: str | None = None
    status: str | None = None
    description: str | None = None
    member_type: str | None = Field(default=None, alias="memberType")
    uid: str | None = None
    unique_name: str | None = Field(default=None, alias="uniqueName")
    domain_name: str | None = Field(default=None, alias="domainName")
    not_found: bool | None = Field(default=None, alias="notFound")
