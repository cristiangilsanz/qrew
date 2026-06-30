from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class PasskeyResponse(BaseModel):
    id: str
    name: str | None
    aaguid: str
    last_used_at: datetime | None
    created_at: datetime


class PasskeyListResponse(BaseModel):
    passkeys: list[PasskeyResponse]


class PasskeyRenameRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)


class AttestationResponseData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    client_data_json: str = Field(alias="clientDataJSON")
    attestation_object: str = Field(alias="attestationObject")


class PasskeyRegistrationCompleteRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    raw_id: str = Field(alias="rawId")
    response: AttestationResponseData
    type: str = "public-key"


class PasskeyRegistrationCompleteResponse(BaseModel):
    message: str


class AssertionResponseData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    client_data_json: str = Field(alias="clientDataJSON")
    authenticator_data: str = Field(alias="authenticatorData")
    signature: str
    user_handle: str | None = Field(alias="userHandle", default=None)


class PasskeyAuthenticationBeginRequest(BaseModel):
    email: EmailStr


class PasskeyAuthenticationCompleteRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    raw_id: str = Field(alias="rawId")
    response: AssertionResponseData
    type: str = "public-key"


class PasskeyAssertBeginResponse(BaseModel):
    options: str


class PasskeyAssertCompleteResponse(BaseModel):
    asserted_at: datetime
