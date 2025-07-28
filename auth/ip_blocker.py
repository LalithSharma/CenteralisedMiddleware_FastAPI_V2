from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.status import HTTP_403_FORBIDDEN
from auth.database import SessionLocal
from users.models import BlocklistEntry


class IPBlockMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.headers.get("X-Forwarded-For") or request.client.host
        db = SessionLocal()
        try:
            blocked_ips = (
                db.query(BlocklistEntry)
                .filter(BlocklistEntry.type == "ip")
                .with_entities(BlocklistEntry.value)
                .all()
            )
            blocked_ip_list = [ip[0] for ip in blocked_ips if ip[0]]

            if client_ip in blocked_ip_list:
                return Response("Access Denied: IP blocked", status_code=HTTP_403_FORBIDDEN)
        finally:
            db.close()
            
        response = await call_next(request)
        return response