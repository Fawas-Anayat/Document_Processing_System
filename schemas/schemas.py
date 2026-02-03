from pydantic import BaseModel , EmailStr , Field
from fastapi import File , UploadFile 
from datetime import datetime

class User_schema(BaseModel):

    name : str = Field(... , min_length=3 , max_length=20)
    email : EmailStr = Field(...)
    password :str = Field(... , min_length=5 , max_length=16)

class Document_schema(BaseModel):

    file_size : int
    file_path : str
    upload_time : datetime

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class LogoutRequest(BaseModel):
    refresh_token: str

class ChatRequest(BaseModel):
    document_id: int
    query: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": 5,
                "query": "What is machine learning?"
            }
        }


