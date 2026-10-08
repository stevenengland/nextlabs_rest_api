"""CloudAz composite membership conditions."""

from pydantic import BaseModel, ConfigDict, Field

from nextlabs_sdk._cloudaz._member_dto import MemberDTO


class MemberCondition(BaseModel):
    """An operator over a list of composite members.

    Known operators are IN and NOT; other vendor values are retained.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    operator: str | None = None
    members: list[MemberDTO] = Field(default_factory=list)
