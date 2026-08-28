# reverse proxies api requests to the domain service named in the path
import structlog
from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse
from httpx import AsyncClient

from com.qode.qrew.v1.gateway.core.config import settings

logger = structlog.get_logger(__name__)

router = APIRouter()

_HOP_BY_HOP = frozenset(
    [
        "host",
        "connection",
        "transfer-encoding",
        "te",
        "trailers",
        "upgrade",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "access-control-allow-origin",
        "access-control-allow-credentials",
        "access-control-allow-methods",
        "access-control-allow-headers",
        "access-control-expose-headers",
        "access-control-max-age",
    ]
)

_UPSTREAMS: dict[str, str] = {
    "identity": settings.identity_url,
    "catalog": settings.catalog_url,
    "sales": settings.sales_url,
    "payments": settings.payments_url,
    "ticketing": settings.ticketing_url,
    "entry": settings.entry_url,
}


# returns the shared http client used to reach every upstream
def _get_client(request: Request) -> AsyncClient:
    return request.app.state.proxy_client  # type: ignore[no-any-return]


# strips hop by hop headers and adds the forwarded client address
def _build_upstream_headers(request: Request) -> dict[str, str]:
    headers: dict[str, str] = {
        k: v for k, v in request.headers.items() if k.lower() not in _HOP_BY_HOP
    }
    client_host = request.client.host if request.client else "unknown"
    headers["x-forwarded-for"] = client_host
    headers["x-forwarded-proto"] = request.url.scheme
    return headers


# forwards a request to its upstream service and streams back the response
@router.api_route(
    "/api/{service}/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def proxy(service: str, path: str, request: Request) -> Response:
    upstream = _UPSTREAMS.get(service)
    if upstream is None:
        return Response(
            content=f"Unknown service: {service}",
            status_code=404,
            media_type="text/plain",
        )

    qs = request.url.query
    target = f"{upstream}/{path}"
    if qs:
        target = f"{target}?{qs}"

    headers = _build_upstream_headers(request)
    body = await request.body()

    client = _get_client(request)

    try:
        upstream_resp = await client.request(
            method=request.method,
            url=target,
            headers=headers,
            content=body,
            follow_redirects=False,
        )
    except Exception as exc:
        await logger.aerror("proxy.upstream_error", service=service, path=path, error=str(exc))
        return Response(
            content='{"detail":"upstream unavailable"}',
            status_code=502,
            media_type="application/json",
        )

    response_headers = {
        k: v for k, v in upstream_resp.headers.items() if k.lower() not in _HOP_BY_HOP
    }

    return StreamingResponse(
        content=upstream_resp.aiter_bytes(),
        status_code=upstream_resp.status_code,
        headers=response_headers,
        media_type=upstream_resp.headers.get("content-type"),
    )
