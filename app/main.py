from fastapi import FastAPI , Depends , UploadFile , File , HTTPException , status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from db.db import get_db
from models.models import User , Document
from db.db import Base , engine
from schemas.schemas import User_schema
from auth.auth import validate_pdf_file , hash_password , authenticate_user , create_tokens
from fastapi.security import OAuth2PasswordRequestForm
from auth.helper_fun import model_to_dict



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


@app.post("uploadFile")
def upload_file(file : UploadFile = File(...)):
   pass