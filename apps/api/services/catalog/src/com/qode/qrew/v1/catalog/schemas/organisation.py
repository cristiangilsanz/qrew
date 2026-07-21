import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from com.qode.qrew.v1.catalog.models.organisation import OrganisationRole


class OrganisationCreateRequest(BaseModel):
    slug: str = Field(..., min_length=3, max_length=64)
    name: str = Field(..., min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=2000)


class OrganisationResponse(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    description: str | None
    created_at: datetime


class OrganisationPublicResponse(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    description: str | None


class OrganisationSearchResult(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    description: str | None


class OrgMemberListItem(BaseModel):
    user_id: uuid.UUID
    role: OrganisationRole
    joined_at: datetime


class OrganisationMemberInviteRequest(BaseModel):
    email: EmailStr
    role: OrganisationRole = OrganisationRole.member


class OrganisationMemberAddRequest(BaseModel):
    user_id: uuid.UUID
    role: OrganisationRole = OrganisationRole.member


class OrganisationMemberResponse(BaseModel):
    organisation_id: uuid.UUID
    user_id: uuid.UUID
    role: OrganisationRole
    joined_at: datetime
