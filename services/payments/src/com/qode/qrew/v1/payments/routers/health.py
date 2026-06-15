from probes import create_probe_router
from com.qode.qrew.v1.payments.core.database import get_db
from com.qode.qrew.v1.payments.core.dependencies import get_redis

router = create_probe_router(get_db, get_redis)
