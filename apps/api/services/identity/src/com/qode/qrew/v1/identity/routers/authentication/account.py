# exposes the endpoints that change delete and recover an account's credentials
from fastapi import APIRouter, Depends, Request, status

from com.qode.qrew.v1.identity.core.dependencies import get_current_user
from com.qode.qrew.v1.identity.core.dependencies import limiter
from com.qode.qrew.v1.identity.models.user import User
from com.qode.qrew.v1.identity.schemas.account import (
    AccountDeleteRequest,
    AccountDeleteResponse,
    ChangeEmailRequest,
    ChangeEmailResponse,
    ChangePasswordRequest,
    ChangePasswordResponse,
    ChangePhoneRequest,
    ChangePhoneResponse,
    ConfirmEmailChangeRequest,
    ConfirmPhoneChangeRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
)
from com.qode.qrew.v1.identity.services.application.authentication.account.deletion import (
    AccountDeletionError,
    AccountDeletionService,
)
from com.qode.qrew.v1.identity.services.application.authentication.account.changes.forgot_password import (
    ForgotPasswordError,
    ForgotPasswordService,
)
from com.qode.qrew.v1.identity.services.application.authentication.account.changes.email_change import (
    EmailChangeError,
    EmailChangeService,
)
from com.qode.qrew.v1.identity.services.application.authentication.account.changes.password_change import (
    PasswordChangeError,
    PasswordChangeService,
)
from com.qode.qrew.v1.identity.services.application.authentication.account.changes.phone_change import (
    PhoneChangeError,
    PhoneChangeService,
)

from ._deps import (
    domain_error,
    get_deletion_service,
    get_email_change_service,
    get_forgot_password_service,
    get_password_change_service,
    get_phone_change_service,
)

router = APIRouter(prefix="/account")


# changes the caller's password
@router.post(
    "/change-password",
    response_model=ChangePasswordResponse,
    status_code=status.HTTP_200_OK,
    summary="Change the current user's password",
)
@limiter.limit("5/hour")  # type: ignore[misc]
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    service: PasswordChangeService = Depends(get_password_change_service),
) -> ChangePasswordResponse:
    try:
        await service.change_password(current_user, body.current_password, body.new_password)
        return ChangePasswordResponse(message="Password changed successfully.")
    except PasswordChangeError as exc:
        raise domain_error(exc.message, exc.field, status.HTTP_400_BAD_REQUEST) from exc


# soft deletes the caller's account
@router.post(
    "/delete",
    response_model=AccountDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Soft-delete the current user's account",
)
@limiter.limit("5/hour")  # type: ignore[misc]
async def delete_account(
    request: Request,
    body: AccountDeleteRequest,
    current_user: User = Depends(get_current_user),
    service: AccountDeletionService = Depends(get_deletion_service),
) -> AccountDeleteResponse:
    try:
        await service.delete(current_user, body.current_password)
        return AccountDeleteResponse(message="Account deleted.")
    except AccountDeletionError as exc:
        raise domain_error(exc.message, exc.field, status.HTTP_400_BAD_REQUEST) from exc


# requests an email address change
@router.post(
    "/change-email",
    response_model=ChangeEmailResponse,
    status_code=status.HTTP_200_OK,
    summary="Request an email address change",
)
@limiter.limit("3/hour")  # type: ignore[misc]
async def change_email(
    request: Request,
    body: ChangeEmailRequest,
    current_user: User = Depends(get_current_user),
    service: EmailChangeService = Depends(get_email_change_service),
) -> ChangeEmailResponse:
    try:
        await service.request_change(current_user, body.new_email, body.current_password)
        return ChangeEmailResponse(message="Confirmation link sent to your new email address.")
    except EmailChangeError as exc:
        raise domain_error(exc.message, exc.field, status.HTTP_400_BAD_REQUEST) from exc


# confirms a requested email address change
@router.post(
    "/confirm-email-change",
    response_model=ChangeEmailResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm an email address change",
)
@limiter.limit("10/hour")  # type: ignore[misc]
async def confirm_email_change(
    request: Request,
    body: ConfirmEmailChangeRequest,
    service: EmailChangeService = Depends(get_email_change_service),
) -> ChangeEmailResponse:
    try:
        await service.confirm_change(body.token)
        return ChangeEmailResponse(message="Email address updated successfully.")
    except EmailChangeError as exc:
        raise domain_error(exc.message, exc.field, status.HTTP_400_BAD_REQUEST) from exc


# requests a phone number change
@router.post(
    "/change-phone",
    response_model=ChangePhoneResponse,
    status_code=status.HTTP_200_OK,
    summary="Request a phone number change",
)
@limiter.limit("3/hour")  # type: ignore[misc]
async def change_phone(
    request: Request,
    body: ChangePhoneRequest,
    current_user: User = Depends(get_current_user),
    service: PhoneChangeService = Depends(get_phone_change_service),
) -> ChangePhoneResponse:
    try:
        await service.request_change(current_user, body.new_phone_number, body.current_password)
        return ChangePhoneResponse(message="Verification code sent to your new phone number.")
    except PhoneChangeError as exc:
        raise domain_error(exc.message, exc.field, status.HTTP_400_BAD_REQUEST) from exc


# confirms a requested phone number change
@router.post(
    "/confirm-phone-change",
    response_model=ChangePhoneResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm a phone number change",
)
@limiter.limit("10/hour")  # type: ignore[misc]
async def confirm_phone_change(
    request: Request,
    body: ConfirmPhoneChangeRequest,
    current_user: User = Depends(get_current_user),
    service: PhoneChangeService = Depends(get_phone_change_service),
) -> ChangePhoneResponse:
    try:
        await service.confirm_change(current_user, body.new_phone_number, body.otp)
        return ChangePhoneResponse(message="Phone number updated successfully.")
    except PhoneChangeError as exc:
        raise domain_error(exc.message, exc.field, status.HTTP_400_BAD_REQUEST) from exc


# requests a password reset link without disclosing whether the email exists
@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    status_code=status.HTTP_200_OK,
    summary="Request a password reset link",
)
@limiter.limit("5/hour")  # type: ignore[misc]
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    service: ForgotPasswordService = Depends(get_forgot_password_service),
) -> ForgotPasswordResponse:
    await service.request_reset(body.email)
    return ForgotPasswordResponse(
        message="If an account with that email exists, a reset link has been sent."
    )


# resets a password using a reset token
@router.post(
    "/reset-password",
    response_model=ResetPasswordResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset password using a token",
)
@limiter.limit("10/hour")  # type: ignore[misc]
async def reset_password(
    request: Request,
    body: ResetPasswordRequest,
    service: ForgotPasswordService = Depends(get_forgot_password_service),
) -> ResetPasswordResponse:
    try:
        await service.reset_password(body.token, body.new_password)
        return ResetPasswordResponse(message="Password reset successfully. You can now sign in.")
    except ForgotPasswordError as exc:
        raise domain_error(exc.message, exc.field, status.HTTP_400_BAD_REQUEST) from exc
