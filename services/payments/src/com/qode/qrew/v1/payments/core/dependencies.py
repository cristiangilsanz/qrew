from db import create_redis_dependency
from fastapi import Depends
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.payments.core.config import settings
from com.qode.qrew.v1.payments.core.database import get_db
from com.qode.qrew.v1.payments.repositories.payment import PaymentRepository
from com.qode.qrew.v1.payments.services import StripeClient, StripeRealClient
from com.qode.qrew.v1.payments.services.payment import PaymentService

limiter = Limiter(key_func=get_remote_address, enabled=settings.ratelimit_enabled)

get_redis = create_redis_dependency(settings.redis_url)

_stripe_client: StripeClient = StripeRealClient()


def get_stripe_client() -> StripeClient:
    return _stripe_client


def get_payment_service(
    db: AsyncSession = Depends(get_db),
    stripe: StripeClient = Depends(get_stripe_client),
) -> PaymentService:
    return PaymentService(db, PaymentRepository(db), stripe)
