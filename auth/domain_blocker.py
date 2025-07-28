# app/middleware/domain_blocker.py

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.status import HTTP_403_FORBIDDEN
from auth.blocklist_cache import blocked_domains


class DomainBlockMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        host_header = request.headers.get("host", "")
        domain_only = host_header.split(":")[0].lower()
        if domain_only in blocked_domains:
            return Response("Access Denied: Domain blocked", status_code=HTTP_403_FORBIDDEN)

        return await call_next(request)
