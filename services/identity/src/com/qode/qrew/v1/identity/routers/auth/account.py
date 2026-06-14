from fastapi import APIRouter, Depends, Request, status

from com.qode.qrew.v1.identity.services.auth.auth import get_current_user
from com.qode.qrew.v1.identity.services.infra.limiter import limiter
from com.qode.qrew.v1.identity.models.auth.user import User
from com.qode.qrew.v1.identity.schemas.account.account import (
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
)
from com.qode.qrew.v1.identity.services.account.account_deletion import (
    AccountDeletionError,
    AccountDeletionService,
)
from com.qode.qrew.v1.identity.services.account.email_change import (
    EmailChangeError,
    EmailChangeService,
)
from com.qode.qrew.v1.identity.services.account.password_change import (
    PasswordChangeError,
    PasswordChangeService,
)
from com.qode.qrew.v1.identity.services.account.phone_change import (
    PhoneChangeError,
    PhoneChangeService,
)

from ._deps import (
    domain_error,
    get_account_deletion_service,
    get_email_change_service,
    get_password_change_service,
    get_phone_change_service,
)

router = APIRouter()


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
    """Change the current user's password."""
    try:
        await service.change_password(current_user, body.current_password, body.new_password)
        return ChangePasswordResponse(message="Password changed successfully.")
    except PasswordChangeError as exc:
        raise domain_error(exc.message, exc.field, status.HTTP_400_BAD_REQUEST) from exc


@router.post(
    "/account/delete",
    response_model=AccountDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Soft-delete the current user's account",
)
@limiter.limit("5/hour")  # type: ignore[misc]
async def delete_account(
    request: Request,
    body: AccountDeleteRequest,
    current_user: User = Depends(get_current_user),
    service: AccountDeletionService = Depends(get_account_deletion_service),
) -> AccountDeleteResponse:
    """Soft-delete the current user's account."""
    try:
        await service.delete(current_user, body.current_password)
        return AccountDeleteResponse(message="Account deleted.")
    except AccountDeletionError as exc:
        raise domain_error(exc.message, exc.field, status.HTTP_400_BAD_REQUEST) from exc


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
    """Request an email address change."""
    try:
        await service.request_change(current_user, body.new_email, body.current_password)
        return ChangeEmailResponse(message="Confirmation link sent to your new email address.")
    except EmailChangeError as exc:
        raise domain_error(exc.message, exc.field, status.HTTP_400_BAD_REQUEST) from exc


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
    """Confirm an email address change."""
    try:
        await service.confirm_change(body.token)
        return ChangeEmailResponse(message="Email address updated successfully.")
    except EmailChangeError as exc:
        raise domain_error(exc.message, exc.field, status.HTTP_400_BAD_REQUEST) from exc


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
    """Request a phone number change."""
    try:
        await service.request_change(current_user, body.new_phone_number, body.current_password)
        return ChangePhoneResponse(message="Verification code sent to your new phone number.")
    except PhoneChangeError as exc:
        raise domain_error(exc.message, exc.field, status.HTTP_400_BAD_REQUEST) from exc


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
    """Confirm a phone number change."""
    try:
        await service.confirm_change(current_user, body.new_phone_number, body.otp)
        return ChangePhoneResponse(message="Phone number updated successfully.")
    except PhoneChangeError as exc:
        raise domain_error(exc.message, exc.field, status.HTTP_400_BAD_REQUEST) from exc
