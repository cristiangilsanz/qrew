from pydantic import BaseModel, Field


class SignUploadRequest(BaseModel):
    kind: str = Field(..., max_length=32)
    content_type: str = Field(..., max_length=64)
    size_bytes: int = Field(..., gt=0)


class SignUploadResponse(BaseModel):
    key: str
    upload_url: str
    expires_at: int
    max_size_bytes: int
