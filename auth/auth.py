from fastapi import UploadFile , HTTPException , status , Depends
import os
from settings.settings import ALLOWED_FILE_TYPES
from schemas.schemas import User_schema
from passlib.context import CryptContext
from schemas.schemas import User_schema
from models.models import User , RefreshToken
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Optional
from datetime import timedelta , datetime
from jose import JWTError, jwt
import secrets



ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7
SECRET_KEY="mysecertkey"
ALGORITHN ="HS256"



pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def authenticate_user(email : str , password : str ,db:Session):
    user=db.query(User).filter(User.email == email).first()
    if not user:
        return False
    
    if not verify_password(password, user.hashed_password):
        return False
    
    return user  

def get_current_user():
    pass

def validate_pdf_file(file : UploadFile , user : User_schema = Depends(get_current_user)):
    if file.content_type not in  ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST , detail="wrong file type , can only upload pdf file"
        )

def create_access_token(data : dict,expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta

    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp" : expire})

    encoded_jwt = jwt.encode(to_encode,SECRET_KEY , algorithm=ALGORITHN)
    return encoded_jwt

def create_refresh_token(data : dict , db:Session):
    now = datetime.utcnow()
    expire= datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": data["name"],          
        "iat": now,               
        "exp": expire,            
        "user_id": data["id"],       
        "type": "refresh",       
        "jti": secrets.token_urlsafe(32)  
    }
    
    encoded_ref_token =jwt.encode(payload , SECRET_KEY , algorithm=ALGORITHN)
    save_refresh_db(data,encoded_ref_token,db)

    return encoded_ref_token

def create_tokens(user: User , db:Session) -> dict:

    access_token = create_access_token(user)
    refresh_token = create_refresh_token(user,db)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

def save_refresh_db(data:dict, encoded_ref_token : RefreshToken , db: Session):
    payload = jwt.decode(encoded_ref_token, SECRET_KEY, algorithms=[ALGORITHN])
    jti = payload.get("jti")
    iat = payload.get("iat")
    expires_at = datetime.fromtimestamp(payload.get("exp"))
    token_hash = pwd_context.hash(encoded_ref_token)

    db_token = RefreshToken(
        user_id=data["id"],
        token=token_hash,
        expires_at=expires_at ,
        created_at = iat
    )

    db.add(db_token)
    db.commit()


