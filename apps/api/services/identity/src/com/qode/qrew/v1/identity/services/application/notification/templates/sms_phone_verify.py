def verification_otp_sms(otp: str, expire_minutes: int) -> str:
    return (
        f"Your Qrew verification code is: {otp}\n"
        f"It expires in {expire_minutes} minutes.\n"
        f"Do not share this code with anyone."
    )
