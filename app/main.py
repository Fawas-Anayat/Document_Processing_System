from fastapi import FastAPI , Depends , UploadFile , File , HTTPException , status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from db.db import get_db
from models.models import User , Document , BlacklistedAccessTokens , RefreshToken 
from db.db import Base , engine
from schemas.schemas import User_schema , RefreshTokenRequest
from auth.auth import hash_password , authenticate_user , create_tokens , oauth2_scheme , ALGORITHN , SECRET_KEY , get_current_user , verify_refresh_token , refresh_access_token
from fastapi.security import OAuth2PasswordRequestForm
from auth.helper_fun import model_to_dict
from jose import jwt
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
def logout(current_user = Depends(get_current_user) , db: Session = Depends(get_db) , token = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHN])

        jti = payload.get("jti")
        exp = payload.get("exp")
        user_id = payload.get("user_id")
        
        refresh_tokens = db.query(RefreshToken).filter(RefreshToken.user_id == user_id).all()

        if refresh_tokens:
            for ref_token in refresh_tokens :
                ref_token.is_revoked = True


        if jti and exp:
            expires_at = datetime.fromtimestamp(exp)

            existing = db.query(BlacklistedAccessTokens).filter(
                BlacklistedAccessTokens.jti == jti
            ).first()

            if not existing:
                blacklisted_access_token = BlacklistedAccessTokens(
                    jti = jti ,
                    user_id=current_user.id ,
                    blacklisted_at = datetime.utcnow() ,
                    expires_at = expires_at
                )
                db.add(blacklisted_access_token)

            db.commit()
            return {"message" : "log out successful"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {str(e)}"
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