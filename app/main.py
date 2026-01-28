from fastapi import FastAPI , Depends , UploadFile , File , HTTPException , status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from db.db import get_db
from models.models import User , Document , BlacklistedAccessTokens , RefreshToken , RevokedTokens
from db.db import Base , engine
from schemas.schemas import User_schema
from auth.auth import validate_pdf_file , hash_password , authenticate_user , create_tokens , oauth2_scheme , ALGORITHN , SECRET_KEY
from auth.helper_fun import get_current_user
from fastapi.security import OAuth2PasswordRequestForm
from auth.helper_fun import model_to_dict
from jose import jwt
from datetime import datetime , timedelta


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
    user =model_to_dict(authenticate_user(email=form_data.username , password=form_data.password,db=db))

    if user is False:
        raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="invalid username or password"
    )

    tokens = create_tokens(user,db)

    return tokens

@app.post("/logout")
def logout(current_user = Depends(get_current_user) , db: Session = Depends(get_db) , token = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHN])

        jti = payload.get("jti")
        exp = payload.get("exp")
        user_id = payload.get("user_id")
        
        refresh_token = db.query(RefreshToken).filter(RefreshToken.user_id == user_id).first()

        if refresh_token:
            refresh_token.is_revoked = True
            
            new_revoke_token = RevokedTokens(
                user_id = user_id ,
                jti = refresh_token.jti,
                token_type = 1 ,
                revoked_at = datetime.utcnow() ,
                expires_at = refresh_token.expires_at
            )
            db.commit()

        if jti and exp:
            expires_at = datetime.fromtimestamp(exp)

            existing = db.query(BlacklistedAccessTokens).filter(
                BlacklistedAccessTokens.jti == jti
            ).first()

            if not existing:
                blacklisted_access_token = BlacklistedAccessTokens(
                    jti = jti ,
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




        
    




@app.post("uploadFile")
def upload_file(file : UploadFile = File(...)):
   pass