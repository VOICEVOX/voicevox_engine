from pydantic import BaseModel, Field
from datetime import datetime


class TokenSchema(BaseModel):
    access_token: str
    refresh_token: str
    
    
class TokenPayload(BaseModel):
    sub: str = None
    exp: int = None


class UserAuth(BaseModel):
    email: str = Field(..., description="user email")
    username: str = Field(..., description="user name")
    password: str = Field(..., min_length=5, max_length=24, description="user password")
    

class UserOut(BaseModel):
    id: int
    email: str
    username : str


class SystemUser(UserOut):
    password: str
    is_active: bool

    class Config:
        orm_mode = True


class ConversationCreate(BaseModel):
    user_id: int


class Conversation(BaseModel):
    user_id: int
    request: str
    response: str
    created_date: datetime


class MessageCreate(BaseModel):
    conversation_id: int
    request: str
    response: str
