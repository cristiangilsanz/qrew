from probes import create_probe_router
from com.qode.qrew.v1.identity.core.database import get_db
from com.qode.qrew.v1.identity.core.dependencies import get_redis

router = create_probe_router(get_db, get_redis)
