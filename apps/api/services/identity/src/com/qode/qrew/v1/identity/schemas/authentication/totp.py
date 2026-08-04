from pydantic import BaseModel, Field


class TotpSetupResponse(BaseModel):
    provisioning_uri: str
    backup_codes: list[str]
    secret: str


class TotpConfirmRequest(BaseModel):
    secret: str
    code: str = Field(..., min_length=6, max_length=10)
    backup_codes: list[str]


class TotpConfirmResponse(BaseModel):
    message: str


class TotpVerifyRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=10)


class TotpVerifyResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105


class TotpDisableRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=10)


class TotpDisableResponse(BaseModel):
    message: str


class TotpStatusResponse(BaseModel):
    enabled: bool
