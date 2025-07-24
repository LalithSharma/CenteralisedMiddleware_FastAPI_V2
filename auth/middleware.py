import asyncio
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
import os
import time
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
#from sqlalchemy import select
from auth.dependencies import validate_token
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
#from auth.routes import get_blocklist

from logger import log_error, log_info

logger = logging.getLogger('uvicorn.access')
logger.disabled = False

def ApiGateway_Middleware(app:FastAPI):
    Middle_logs_dir = os.path.join(os.getcwd(), "logs/static", "middlewarelogs")
    os.makedirs(Middle_logs_dir, exist_ok=True)
    
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    Middlelog_file_name = os.path.join(Middle_logs_dir, f"{current_time}.log")
    
    log_formatter = logging.Formatter(
        "%(log_type): %(asctime) - IP: %(client_ip) - Domain: %(host)s - URL: %(url)s - Token: %(token)s - Method: %(method)s - LogMessage: %(log_message)s"
    )
    log_handler = RotatingFileHandler(
        Middlelog_file_name, maxBytes=10 * 1024 * 1024, backupCount=5
    )
    log_handler.setFormatter(log_formatter)
    logger = logging.getLogger("api_gateway_logger")
    logger.setLevel(logging.INFO)
    logger.addHandler(log_handler)
    
    @app.middleware('http')

    async def custom_logging(request: Request, call_next):
        if request.url.path.startswith("/logs/apilogs/"):
            return await call_next(request)
        start_time = time.time()
        client_ip = request.client.host
        domain = request.headers.get("host", "unknown")
        
        token = request.headers.get("Authorization", "none")
        
        if not token:
            return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
        url = str(request.url)
        method = request.method

        # query_ip = select(BlocklistEntry).where(
        #         (BlocklistEntry.c.type == BlockTypeEnum.ip)
        #         & (BlocklistEntry.c.value == client_ip)
        #     )
        
        # blocked_ip = await db.fetch_one(query_ip)
        # if blocked_ip:
        #     return JSONResponse(status_code=403, content={"detail": "Access denied: IP blocked."})

        # # --- Check if domain is blocked ---
        # query_domain = select(BlocklistEntry).where(
        #     (BlocklistEntry.c.type == BlockTypeEnum.domain)
        #     & (BlocklistEntry.c.value == domain)
        # )
        # blocked_domain = await get_blocklist(query_domain)
        # if blocked_domain:
        #     return JSONResponse(status_code=403, content={"detail": "Access denied: Domain blocked."})

        incoming_log_data = {
            "log_type": "INCOMING",
            "client_ip": client_ip,
            "host": domain,
            "url": url,
            "token": token,
            "method": method,
            "log_message": "Incoming request received",
        }
        logger.info("Incoming request log", extra=incoming_log_data)

        print(incoming_log_data)
        try:
            response = await call_next(request)
            processed_time = time.time() - start_time
            outgoing_log_data = {
                "log_type": "OUTGOING",
                "client_ip": client_ip,
                "host": domain,
                "url": url,
                "token": token,
                "method": method,
                "status_code": response.status_code,
                "processed_time": f"{processed_time:.2f}s",
                "log_message": "Outgoing response sent",
            }
            logger.info("Outgoing request log", extra=outgoing_log_data) 
            print(outgoing_log_data)
            return response
        
        except Exception as e:
            processed_time = time.time() - start_time
            error_log_data = {
            "log_type": "ERROR",
            "client_ip": client_ip,
            "host": domain,
            "url": url,
            "token": token,
            "method": method,
            "processed_time": f"{processed_time:.2f}s",
            "error": str(e),
            "log_message": "Error occurred while processing request",
            }
            logger.error("Error while processing request", extra=error_log_data)
            return JSONResponse(
                status_code=500,
                content={"detail": "An internal server error occurred."},
            )     

    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],allow_credentials= True,)
    app.add_middleware(TrustedHostMiddleware,  allowed_hosts=["centeralisedmiddleware.onrender.com","mpp-gateway-ewpuz.ondigitalocean.app","127.0.0.1", "localhost", "*.yourdomain.com"],)

def admin_only(request: Request):    
    # Get the role from the cookies
    client_ip = request.client.host
    host = request.headers.get("host", "unknown")
    token = request.headers.get("Authorization", "none")
    Logged_token = request.cookies.get("access_token")  
    if not Logged_token:
        log_error(client_ip, host, "/get admin", token, "Token is missing")
        raise HTTPException(status_code=401, detail="Token is missing")  
    user_Token = validate_token(Logged_token)
    log_info(client_ip, host, "/get admin", token, f"user token fetched to check user role: {user_Token}")
    UserLogged_Role = user_Token["role"]
    log_info(client_ip, host, "/get admin", token, f"Roles fetched: {UserLogged_Role}")
    if not UserLogged_Role:
        log_error(client_ip, host, "/get admin", token, "Not authenticated")
        raise HTTPException(status_code=401, detail="Not authenticated")    
    if "admin" not in UserLogged_Role:
        log_error(client_ip, host, "/get admin", token, "Permission denied")
        raise HTTPException(status_code=403, detail="Permission denied")    
    return True 
