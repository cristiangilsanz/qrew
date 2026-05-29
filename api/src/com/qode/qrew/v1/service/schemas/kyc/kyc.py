from pydantic import BaseModel


class KycUploadResponse(BaseModel):
    message: str
    kyc_status: str
