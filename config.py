# config.py
from pydantic_settings import BaseSettings
from typing import Optional
from pydantic import Field

class Settings(BaseSettings):    


    groq_api_key: str = Field(..., env="GROQ_API_KEY")
    secret_key : str
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  
    ALLOWED_EXTENSIONS: list = [".pdf", ".docx", ".txt"]
    
    CHROMA_DB_DIR: str = "./chroma_db"
    
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    CHUNK_SIZE: int = 1000  
    CHUNK_OVERLAP: int = 200 
    EMBEDDING_DIMENSION : Optional [int] = None

    OPENAI_API_KEY: Optional[str] = None
    LLM_MODEL: str = "gpt-3.5-turbo"
    
    class Config:
        env_file = ".env" 
        case_sensitive = False 

settings = Settings()