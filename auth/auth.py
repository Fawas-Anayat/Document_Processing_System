from fastapi import UploadFile , HTTPException , status , Depends
import os
from settings.settings import ALLOWED_FILE_TYPES
from passlib.context import CryptContext
from schemas.schemas import User_schema
from models.models import User , RefreshToken , BlacklistedAccessTokens
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Optional
from datetime import timedelta , datetime
from jose import JWTError, jwt
import secrets
import uuid
from db.db import get_db


ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7
SECRET_KEY = os.getenv("SECRET_KEY", "mysecertkey")
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

def get_current_user( token : str = Depends(oauth2_scheme) ,
        db : Session = Depends(get_db)):
    payload = verify_token(token, db)
    user_email = payload.get("email")
    user = db.query(User).filter(User.email == user_email).first()
    if not user :
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND , detail="no user found with this information"
        )
    
    return user

def create_access_token(data : dict,expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    jti_id = str(uuid.uuid4())

    iat_ts = int(datetime.utcnow().timestamp())
    exp_ts = int(expire.timestamp())
    to_encode.update({"jti": jti_id})
    to_encode.update({
        "iat": iat_ts,
        "exp": exp_ts,
        "user_id": data["id"],
        "email": data["email"],
        "name": data.get("name"),
        "type": "access"
    })

    encoded_jwt = jwt.encode(to_encode,SECRET_KEY , algorithm=ALGORITHN)
    return encoded_jwt

def create_refresh_token(data : dict , db:Session):
    now = datetime.utcnow()
    expire = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    iat_ts = int(now.timestamp())
    exp_ts = int(expire.timestamp())

    payload = {
        "sub": data["name"],
        "iat": iat_ts,
        "exp": exp_ts,
        "user_id": data["id"],
        "type": "refresh",
        "jti": str(uuid.uuid4())
    }

    encoded_ref_token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHN)
    save_refresh_db(data, encoded_ref_token, db)

    return encoded_ref_token

def create_tokens(user: dict , db:Session) -> dict:

    access_token = create_access_token(user)
    refresh_token = create_refresh_token(user,db)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

def save_refresh_db(data:dict, encoded_ref_token : str , db: Session):
    payload = jwt.decode(encoded_ref_token, SECRET_KEY, algorithms=[ALGORITHN])
    jti = payload.get("jti")
    iat = payload.get("iat")
    expires_at = datetime.fromtimestamp(payload.get("exp"))
    token_hash = pwd_context.hash(encoded_ref_token)

    db_token = RefreshToken(
        user_id=data["id"],
        token=token_hash,
        expires_at=expires_at ,
        created_at = datetime.fromtimestamp(iat) ,
        jti = jti
    )

    db.add(db_token)
    db.commit()

def verify_token(token: str, db: Session) -> dict:
    """Verify access token and check if blacklisted."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHN])

        jti = payload.get("jti")
        token_type = payload.get("type")

        if token_type != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")

        # Check if token is blacklisted (user logged out)
        blacklisted = db.query(BlacklistedAccessTokens).filter(
            BlacklistedAccessTokens.jti == jti
        ).first()

        if blacklisted:
            raise HTTPException(
                status_code=401,
                detail="Token has been revoked"
            )

        return payload
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )



def verify_refresh_token(token: str, db: Session) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHN])
        
        token_type = payload.get("type")
        if token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type. Expected refresh token",
            )
        
        jti = payload.get("jti")
        user_id = payload.get("user_id")
        
        if not jti or not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token structure",
            )
        
        refresh_token_db = db.query(RefreshToken).filter(
            RefreshToken.jti == jti,
            RefreshToken.user_id == user_id
        ).first()
        
        if not refresh_token_db:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token not found",
            )
        
        if refresh_token_db.is_revoked:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked. Please log in again",
            )
        
        if datetime.utcnow() > refresh_token_db.expires_at:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired. Please log in again",
            )
        
        return payload
        
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )


def refresh_access_token(refresh_token: str, db: Session) -> dict:

    payload = verify_refresh_token(refresh_token, db)
    
    user_id = payload.get("user_id")
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    user_data = {
        "id": user.id,
        "email": user.email,
        "name": user.name
    }

    ref_old_token = db.query(RefreshToken).filter(RefreshToken.user_id == user_data['id']).first()
    if ref_old_token:
        ref_old_token.is_revoked = True
        db.add(ref_old_token)
        db.commit()

    new_refresh_token = create_refresh_token(user_data, db)
    new_access_token = create_access_token(user_data)
    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

