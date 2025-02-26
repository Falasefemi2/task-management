from pydantic import BaseModel
from typing import Optional

class TaskBase(BaseModel):
    title: str
    description: str

class TaskCreate(TaskBase):
    completed: bool

class TaskCreateResponse(TaskBase):
    id: int
    completed: bool
    owner_id: int
    message: str

    class Config:
        from_attributes = True  # Changed from orm_mode = True
        
class TaskResponse(BaseModel):
    id: int
    title: str
    description: str
    completed: bool
    owner_id: int

    class Config:
        from_attributes = True  # Changed from orm_mode = True
        
class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int

    class Config:
        from_attributes = True  # Changed from orm_mode = True
        
class TokenResponse(BaseModel):
    access_token: str
    token_type: str

class UserRegisterResponse(BaseModel):
    message: str
    username: str
    access_token: str  # JWT token for authentication
    token_type: str = "Bearer"
