# defines the response schema for a kyc document upload
from pydantic import BaseModel


class KycUploadResponse(BaseModel):
    message: str
    kyc_status: str
