from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    status: Optional[str] = "active"

class UserCreate(UserBase):
    password: str
    channels: str
    role: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None

class UserOut(UserBase):
    id: int
    created_date: datetime
    update_date: Optional[datetime] = None

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    status: str
    
    class Config:
        orm_mode = True

class LogFile(BaseModel):
    filename: str
    size: int  # in bytes
    created_at: datetime
    
class LogFilesResponse(BaseModel):
    message: str
    result: bool
    data: List[LogFile]
    
class BlockRequest(BaseModel):
    blocked_ips: List[str]
    blocked_domains: List[str]