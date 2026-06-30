from pydantic import BaseModel, Field


class QueueJoinResponse(BaseModel):
    position: int


class QueuePositionResponse(BaseModel):
    position: int | None


class QueueRedeemRequest(BaseModel):
    redeem_window_token: str = Field(..., min_length=1)


class QueueRedeemResponse(BaseModel):
    reservation_window_token: str
