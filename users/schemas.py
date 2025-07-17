from typing import List
from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserSchema(UserBase):
    id: int
    email: EmailStr
    status: str
    channels: List[str]
    role: List[str]

    class Config:
        from_attributes = True
        
class UserInsert(UserBase):
    id: int
    email: EmailStr
    status: str
    
    class Config:
        from_attributes = True
        