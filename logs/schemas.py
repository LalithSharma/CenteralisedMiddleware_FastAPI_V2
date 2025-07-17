from pydantic import BaseModel
from typing import List
from datetime import datetime

class LogFile(BaseModel):
    filename: str
    size: int  # in bytes
    created_at: datetime
    
class LogFilesResponse(BaseModel):
    message: str
    result: bool
    data: List[LogFile]