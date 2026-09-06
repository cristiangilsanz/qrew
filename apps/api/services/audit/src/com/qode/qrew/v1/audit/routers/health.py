# exposes the health probe endpoints for the audit service
from probes import create_probe_router

from com.qode.qrew.v1.audit.core.database import get_db
from com.qode.qrew.v1.audit.core.dependencies import get_redis

router = create_probe_router(get_db, get_redis)
