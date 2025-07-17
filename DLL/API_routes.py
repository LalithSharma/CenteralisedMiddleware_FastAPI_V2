import logging
import os
import re
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, Path, Request
from auth.dependencies import fetch_channel_data, fetch_urls, get_current_user, get_db
import httpx
import json
from redis.asyncio import Redis
from logger import log_error, log_info
from DLL.utils import RateLimitConfig, RateLimiter
from users.models import APIRoute, StatusEnum

router = APIRouter()
redis_url = os.getenv("REDIS_URL")
redis_client = Redis.from_url(redis_url, decode_responses=True)

config = RateLimitConfig(max_calls=60, period=60)
rate_limiter = RateLimiter(redis_client, config)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# DYNAMIC_PATHS_FROM_DB = [
#     "/clients",
#     "/clients/{client_id}",
#     "/clients/{client_id}/products",
#     "/clients/{client_id}/products/{product_id}",
#     "/clients/{client_id}/products/{product_id}/calendar",
#     "/clients/{client_id}/receptionists",
#     "/clients/{client_id}/receptionists/{receptionist_id}",
#     "/clients/{client_id}/commissions",
#     "/clients/{client_id}/commissions/{commission_id}",
#     "/clients/{client_id}/orders",
#     "/clients/{client_id}/orders/{order_id}",
#     "/clients/{client_id}/orders/invoice/{invoice_id}",
#     "/clients/{client_id}/orders/attachment/{attachment_id}",
#     "/clients/{client_id}/orders/voucher/{voucher_id}",
#     "/clients/{client_id}/orders/prepaidvoucher/{prepaidvoucher_id}",
# ]

@router.get("/{full_path:path}")
async def handle_dynamic_routes(
    request: Request,
    channel: str = Path(..., description="Service prefix from URL"),
    full_path: str = Path(..., description="Dynamic subpath"),
    token_data: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    request_path = "/" + full_path

    if not request_path.startswith("/clients"):
        raise HTTPException(status_code=404, detail="Only /clients path is allowed")

    client_ip = request.client.host
    host = request.headers.get("host", "unknown")
    token = request.headers.get("Authorization", "none")
    
    user_channel = getattr(token_data, "channels", None)
    channel_data = fetch_channel_data(channel, db)
    urls_patterns = fetch_urls(db)    
    print("displaye url patterns", urls_patterns)
    if not channel_data:
        log_error(client_ip, host, "/product ids - calendar - user channel", token, f"Channel '{channel}' not found in the database")
        raise HTTPException(
        status_code=404, detail=f"Channel '{channel}' not found in the database"
    ) 
    channelName = channel_data.get("name")
    channelBaseURL = channel_data.get("BaseUrl")
    channelApiKey = channel_data.get("ApiKey")
    channelAuthURL = channel_data.get("AuthUrl")
       
    if not user_channel:
        log_error(client_ip, host, "/product ids - user channel", token, "User's channel is not defined")
        raise HTTPException(status_code=400, detail="User's channel is not defined")
    
    if channelName == 'Error':
        log_error(client_ip, host, "/product ids - user channel", token, "Malformed SOURCE_URL, channel missing")
        raise HTTPException(status_code=500, detail="Malformed SOURCE_URL, channel missing")
    
    if not channelName:
        log_error(client_ip, host, "/product ids - user channel", token, "Invalid API prefix provided")
        raise HTTPException(status_code=400, detail="Invalid API prefix provided")
    
    if channelName not in user_channel:
        log_error(client_ip, host, "/product ids - user channel", token, f"Invalid or unsupported API prefix - user:'{user_channel}', prefix: '{channelName}' in the parameters..")
        raise HTTPException(status_code=400, detail=f"Invalid or unsupported API prefix - user:'{user_channel}', given prefix: '{channelName}' in the parameters..")
    
    if channelName not in channel:
        log_error(client_ip, host, "/product ids - user channel", token, f"Invalid or unsupported API prefix - parameter value:'{channel}', required prefix: '{channelName}' in the paramters..")
        raise HTTPException(status_code=400, detail=f"Invalid or unsupported API prefix - parameter value:'{channel}', required prefix: '{channelName}' in the paramters..")        
    
    core_api_url = f"{channelBaseURL}/{channelName}/{full_path}"
    api_key = channelApiKey
    
    print("core url to get data", core_api_url)
    # Validate if this path is allowed
    dynamic_paths = get_dynamic_paths_from_db(db)
    
    if not is_valid_dynamic_path(request_path, dynamic_paths):
        raise HTTPException(status_code=404, detail="Invalid path")
    
    if is_valid_dynamic_path(request_path, dynamic_paths):
        try:
            matching = next((p for p in dynamic_paths if re.match("^" + re.sub(r"\{[^}]+\}", r"[^/]+", p["path"]) + "$", request_path)), None)
            ttl = matching["maxcache"] if matching else 5
            print("show ttl value", ttl)
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": api_key}
                response = await client.get(core_api_url, headers=headers)
                response.raise_for_status()
                data = response.json()

            cache_key = f"{channel}:{request_path}"
            
            await redis_client.set(cache_key, json.dumps(data), ex=ttl)

            logger.info("Data fetched from core API and cached in Redis.")
            client_ip = request.client.host
            log_info(client_ip, request.headers.get("host"), request_path, "", "Data fetched from core API.")
            return data
        
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
        except Exception as e:
            logger.error(f"Error fetching from core API: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    else:
        raise HTTPException(status_code=404, detail="Invalid path")

# Dynamic Path Matcher
# def is_valid_dynamic_path(path: str) -> bool:
#     for template in DYNAMIC_PATHS_FROM_DB:
#         regex = "^" + re.sub(r"\{[^}]+\}", r"[^/]+", template) + "$"
#         if re.match(regex, path):
#             return True
#     return False

def get_dynamic_paths_from_db(db: Session) -> list[dict]:
    """Fetch all active paths and their maxcache from DB."""
    results = db.query(APIRoute).filter(APIRoute.status == StatusEnum.active).all()
    return [{"path": route.path, "maxcache": route.maxcache} for route in results]

def is_valid_dynamic_path(path: str, paths_from_db: list[dict]) -> bool:
    for entry in paths_from_db:
        template = entry["path"]
        regex = "^" + re.sub(r"\{[^}]+\}", r"[^/]+", template) + "$"
        if re.match(regex, path):
            return True
    return False
