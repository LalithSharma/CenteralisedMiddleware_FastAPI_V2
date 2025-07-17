from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr

from users.models import StatusEnum

class UserRoleChannelOut(BaseModel):
    user_id: int
    email: str
    roles: str
    channels: str
    status: str
    created_at: str

class ShowUsersResponse(BaseModel):
    message: str
    result: bool
    data: List[UserRoleChannelOut]
    
    class Config:
        from_attributes = True

class ShowRoleResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserCreation(BaseModel):
    email: EmailStr
    password: str
    status: str
    roles: List[int]
    channels: List[int]
    
    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None
    status: Optional[str] = None
    roles: Optional[List[int]] = []
    channels: Optional[List[int]] = []
    
    class Config:
        from_attributes = True
    
class ChannelCreate(BaseModel):
    name: str
    base_url: Optional[str] = None
    auth_url: Optional[str] = None
    api_key: Optional[str] = None
    status: StatusEnum

class ChannelUpdate(BaseModel):
    name: Optional[str] = None
    base_url: Optional[str] = None
    auth_url: Optional[str] = None
    api_key: Optional[str] = None
    status: Optional[StatusEnum] = None
    
class ChannelResponse(ChannelCreate):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class ApiRoutePathBase(BaseModel):
    method: str
    path: str
    cache_key_prefix: str
    maxcache: int
    description: Optional[str] = None
    status: StatusEnum = StatusEnum.active

class RoutepathResponse(ApiRoutePathBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True