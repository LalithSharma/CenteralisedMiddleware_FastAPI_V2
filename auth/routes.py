from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import Select
from sqlalchemy.orm import Session

from DLL.schemas import ShowBlockedResponse
from auth.middleware import admin_only
from logger import log_error, log_info
from .dependencies import get_channel_by_name, get_db, authenticate_user, create_access_token, get_user, get_user_channel, get_user_role
from .models import Token
from .schemas import BlockRequest, UserCreate, UserResponse
from users.models import BlocklistEntry, Channel, Role, User, UserAPI, UserChannel, UserRole
from .utils import get_password_hash

router = APIRouter()

@router.post("/login", response_model=Token)
def signin(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    client_ip = request.client.host
    host = request.headers.get("host", "unknown")
    token = request.headers.get("Authorization", "none")
    if not user:
        log_error(client_ip, host, "/sign up", token, "Incorrect username or password - WWW-Authenticate: Bearer")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    role = get_user_role(db, user.id)
    log_info(client_ip, host, "/login", token, f"Roles fetched: {role}")
    access_token, expire_time = create_access_token(data={"sub": user.email, "role": role })
    #db.add(user)
    login_record = UserAPI(
     user_id=user.id,     
     token_type="Bearer",
     unique_token = access_token,
     token_expiration = expire_time,
     login_at=datetime.utcnow()
    )
    db.add(login_record)
    db.commit()
    db.refresh(user)
    log_info(client_ip, host, "/logged with access token", token, "added access token - {access_token},token_type - bearer")
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/signup", response_model= UserResponse, dependencies=[Depends(admin_only)])
def signup(request: Request, user: UserCreate, db: Session = Depends(get_db)):
    
    client_ip = request.client.host
    host = request.headers.get("host", "unknown")
    token = request.headers.get("Authorization", "none")
    db_user = get_user(db, email = user.email)
    if not user:
        log_error(client_ip, host, "/sign up", token, f"User with email '{email}' not found")
        raise HTTPException(status_code=404, detail=f"User with email '{email}' not found")
    
    db_channel = get_channel_by_name(db, channel_name = user.channels)
    if not db_channel:
        log_error(client_ip, host, "/sign up", token, f"Channel with name '{user.channels}' not found")
        raise HTTPException(status_code=404, detail=f"Channel with name '{user.channels}' not found")
    
    # Check if the user is already associated with the channel
    if db_user:
        user_channel = get_user_channel(db, db_user.id, db_channel.id)
        if user_channel:
            log_error(client_ip, host, "/sign up", token, f"User '{user.email}' is already associated with channel '{user.channels}'")
            raise HTTPException(
                status_code=400,
                detail=f"User '{user.email}' is already associated with channel '{user.channels}'")
    
    db_role = db.query(Role).filter(Role.name == user.role).first()
    if not db_role:
        log_error(client_ip, host, "/sign up", token, "Role does not exist, Please entered given Role name.!")
        raise HTTPException(status_code=400, detail="Role does not exist, Please entered given Role name.!")
    
    hashed_password = get_password_hash(user.password)    
    if not db_user:
        db_user = User(
            email=user.email,
            hashed_password=hashed_password,
            status=user.status,
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        log_info(client_ip, host, "/add User", token, f"User added")
    
    user_channel_entry = UserChannel(
        user_id=db_user.id,
        channel_id=db_channel.id,
    )
    db.add(user_channel_entry)
    db.commit()
    log_info(client_ip, host, "/add user channels", token, f"channels added")
            
    user_role_entry = UserRole(
        user_id = db_user.id,
        role_id = db_role.id
    )
    db.add(user_role_entry)
    db.commit()
    log_info(client_ip, host, "/add User ROles", token, f"Role added")
    
    return db_user

@router.post("/blocklist")
async def update_blocklist(data: BlockRequest, db: Session = Depends(get_db)):
    # Store blocked IPs
    for ip in data.blocked_ips:
        if not db.query(BlocklistEntry).filter_by(value=ip, type="ip").first():
            entry = BlocklistEntry(type="ip", value=ip)
            db.add(entry)

    # Store blocked Domains
    for domain in data.blocked_domains:
        if not db.query(BlocklistEntry).filter_by(value=domain, type="domain").first():
            entry = BlocklistEntry(type="domain", value=domain)
            db.add(entry)

    db.commit()
    return {"message": "Blocklist updated successfully"}

@router.get("/showblocked")
async def get_blocklist(db: Session = Depends(get_db)):
    try:
        blocked = db.query(BlocklistEntry).all()
        result = [ShowBlockedResponse.model_validate(ch).model_dump() for ch in blocked]
        return {
            "message": "Blocked List retrieved successfully",
            "result": True,
            "data": result
        }
    except Exception as e:
        # Log the error if you want
        print("Error fetching block list:", e)
        raise HTTPException(status_code=500, detail="Internal server error")
    
    
# async def get_blocklist(query: Select, db: Session = Depends(get_db)) -> Optional[dict]:
#     result = db.execute(query).fetchone()
#     return dict(result._mapping) if result else None
