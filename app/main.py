from fastapi import FastAPI , Depends , UploadFile , File , HTTPException , status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from db.db import get_db
from models.models import User , Document , BlacklistedAccessTokens , RefreshToken 
from db.db import Base , engine
from schemas.schemas import User_schema , RefreshTokenRequest , LogoutRequest
from auth.auth import hash_password , authenticate_user , create_tokens , oauth2_scheme , ALGORITHN , SECRET_KEY , get_current_user , verify_refresh_token , refresh_access_token
from fastapi.security import OAuth2PasswordRequestForm
from auth.helper_fun import model_to_dict
from jose import jwt , JWTError
from datetime import datetime , timedelta
import os

app = FastAPI()

Base.metadata.create_all(bind=engine)


@app.post("/Signup")
def signup_user(user : User_schema , db : Session = Depends(get_db)):
    hashed_password = hash_password(user.password)
    user_db = User(name = user.name , email = user.email , hashed_password = hashed_password)
    db .add(user_db)
    db.commit()
    db.refresh(user_db)

    return {
        "message" :" user registered successfully"
    }

@app.post("/login")
def login_user(form_data : OAuth2PasswordRequestForm = Depends(), db:Session = Depends(get_db)):
    auth_user = authenticate_user(email=form_data.username , password=form_data.password,db=db)
    
    if auth_user is False:
        raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="invalid username or password"
    )
    
    user = model_to_dict(auth_user)

    tokens = create_tokens(user,db)

    return tokens

@app.post("/refresh")
def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    try:
        new_tokens = refresh_access_token(request.refresh_token, db)
        return new_tokens
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token refresh failed: {str(e)}"
        )

@app.post("/logout")
def logout(request : LogoutRequest, db: Session = Depends(get_db) , token = Depends(oauth2_scheme)):
    """
    Logout endpoint: Revokes access token and refresh token.
    
    NOTE: This endpoint accepts EXPIRED access tokens (unlike other protected endpoints).
    This allows users to logout even if their access token has expired.
    
    Required:
    - Authorization header with access token (Bearer <token>) - can be expired
    - Body: {"refresh_token": "<refresh_token>"}
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHN], options={"verify_exp": False})
        
        token_type = payload.get("type")
        if token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token must be an access token"
            )
        
        access_jti = payload.get("jti")
        exp = payload.get("exp")
        user_id = payload.get("user_id")
        
        if not access_jti or not exp or not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid access token structure"
            )

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        db.add(
            BlacklistedAccessTokens(
                jti=access_jti,
                user_id=user_id,
                blacklisted_at=datetime.utcnow(),
                expires_at=datetime.fromtimestamp(exp)
            )
        )

        try:
            refresh_payload = verify_refresh_token(request.refresh_token, db)
            refresh_jti = refresh_payload.get("jti")
            
            if refresh_jti:
                refresh_token_db = db.query(RefreshToken).filter(
                    RefreshToken.jti == refresh_jti,
                    RefreshToken.user_id == user_id
                ).first()

                if refresh_token_db:
                    refresh_token_db.is_revoked = True
                    db.add(refresh_token_db)
        except HTTPException as e:
            # If refresh token is invalid/expired, still blacklist access token
            # This is OK - user can logout with just the access token
            print(f"Info: Refresh token not revoked during logout: {e.detail}")

        # Step 3: Commit all changes
        db.commit()
        return {"message": "Logged out successfully"}

    except HTTPException as e:
        db.rollback()
        raise e
    except JWTError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid access token: {str(e)}"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Logout failed: {str(e)}"
        )

@app.get("/debug/token")
def debug_token(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Debug endpoint to verify token validity (including expired tokens).
    Pass your token in Authorization header to see its contents and validity status.
    """
    try:
        # Decode WITHOUT validating exp so we can see expired tokens too
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHN], options={"verify_exp": False})
        
        jti = payload.get("jti")
        token_type = payload.get("type")
        exp = payload.get("exp")
        
        # Check if blacklisted
        blacklisted = db.query(BlacklistedAccessTokens).filter(
            BlacklistedAccessTokens.jti == jti
        ).first()
        
        is_expired = datetime.utcnow().timestamp() > exp if exp else None
        
        return {
            "valid": True,
            "type": token_type,
            "jti": jti,
            "expires_at": datetime.fromtimestamp(exp).isoformat() if exp else None,
            "is_expired": is_expired,
            "is_blacklisted": blacklisted is not None,
            "payload": payload,
            "current_time": datetime.utcnow().isoformat(),
            "message": "Token is expired. Use /refresh endpoint with refresh_token to get a new access token." if is_expired else "Token is still valid"
        }
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )
    
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )
    




@app.post("/uploadFile")
async def upload_file(file : UploadFile = File(...) , current_user = Depends(get_current_user) , db : Session = Depends(get_db)):
    try:

        if file.content_type not in ["application/pdf"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF files are allowed"
            )
        
        file_content = await file.read()
        file_size = len(file_content)
        
        upload_dir = "uploads"
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        
        file_name = f"{current_user.id}_{datetime.utcnow().timestamp()}_{file.filename}"
        file_path = os.path.join(upload_dir, file_name)
        
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        new_document = Document(
            user_id=current_user.id,
            file_size=str(file_size),
            file_path=file_path,
            upload_time=datetime.utcnow()
        )
        
        db.add(new_document)
        db.commit()
        db.refresh(new_document)
        
        return {
            "message": "File uploaded successfully",
            "file_id": new_document.file_id,
            "file_name": file.filename,
            "file_size": file_size,
            "file_path": file_path,
            "upload_time": new_document.upload_time
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File upload failed: {str(e)}"
        )