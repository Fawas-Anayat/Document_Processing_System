from fastapi import FastAPI , Depends , UploadFile , File , HTTPException , status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from db.db import get_db
from models.models import User , Document , BlacklistedAccessTokens , RefreshToken 
from db.db import Base , engine
from schemas.schemas import User_schema , RefreshTokenRequest , LogoutRequest , ChatRequest
from auth.auth import hash_password , authenticate_user , create_tokens , oauth2_scheme , ALGORITHN , SECRET_KEY , get_current_user , verify_refresh_token , refresh_access_token
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt , JWTError
from datetime import datetime , timedelta
import os
from services.document_processor import document_processor 
from auth.helper_fun import chat_groq_model
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

"""
notes:
origin is the tuple of (scheme + host + port)

"""


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # with the origin we can't allow all the origins because the browsers will reject this, we must specifiy the exact origin  
    allow_credentials=True,    # this means that can we bring in the cookies/credentials along with the requests           
    allow_methods=["*"],                  
    allow_headers=["*"],         # what can we bring in like the content-type or the authorisation etc 
)

Base.metadata.create_all(bind=engine)


@app.post("/Signup")
def signup_user(user : User_schema , db : Session = Depends(get_db)):
    hashed_password = hash_password(user.password)
    user_db = User(name = user.name , email = user.email , hashed_password = hashed_password)
    db.add(user_db)
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
    
    user = {
        "id": auth_user.id,
        "email": auth_user.email,
        "name": auth_user.name
    }


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
            print(f"Info: Refresh token not revoked during logout: {e.detail}")

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
    
@app.post("/uploadFile")
async def upload_file(file : UploadFile = File(...) , current_user = Depends(get_current_user) , db : Session = Depends(get_db)):
    try:
        allowed_file_types = ['application/pdf' , 'docx' , 'txt']
        if file.content_type not in allowed_file_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"invalid file type , only allowed {allowed_file_types}"
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
        
        loaded_doc = document_processor.process_and_store_document_chromadb(file_path=file_path , file_type=file.content_type , user_id=current_user.id ,document_id=new_document.file_id ,db=db)


        return [
            loaded_doc,
            {
            "message": "File uploaded and processed successfully",
            "status" : "file saved in the db and embeddings in the vector db" ,
            "file_name": file.filename,
            "file_size": file_size,
            "file_path": file_path,
            "upload_time": new_document.upload_time
            }
        ]
        
    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File upload failed: {str(e)}"
        )
    
    

@app.post("/ShowDocuments")
def process_documents(current_user = Depends(get_current_user) , db : Session = Depends(get_db)):
    user_documents = db.query(Document).filter(
        Document.user_id == current_user.id,
        Document.processing_status == "completed"
    ).all()

    results = []

    for doc in user_documents:
        collection_name = doc.collection_name
        vector_store = document_processor.get_vector_store(collection_name)
        all_chunks = vector_store.get()
        results.append({
            "file_id": doc.file_id,
            "collection_name": collection_name,
            "chunk_count": len(all_chunks['documents']),
            "chunks": all_chunks['documents'], 
            "metadata": all_chunks['metadatas']  
        })
        return {"documents": results}
    
@app.post("/chat")
def chat(request : ChatRequest ,current_user = Depends(get_current_user) , db : Session = Depends(get_db)):
    document = db.query(Document).filter(
        Document.file_id == request.document_id,
        Document.user_id == current_user.id,
        Document.processing_status == "completed"
    ).first()

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found or not ready"
        )
    
    vector_store = document_processor.get_vector_store(document.collection_name)

    relevant_chunks = vector_store.similarity_search(
        query=request.query,  
        k=5  
    )

    context = "\n\n".join([chunk.page_content for chunk in relevant_chunks])

    prompt = f"""
    You are a helpful assistant. Answer the question based on the context below.
    
    Context from document '{document.file_id}':
    {context}
    
    Question: {request.query}
    
    Answer: Provide a helpful answer based only on the context above. 
    If the answer is not in the context, say "I cannot find this information in the document."
    """

    llm_response = chat_groq_model(prompt , context)

    return {
        "query": request.query,
        "answer": llm_response,
        "source_document": document.file_id,
        "relevant_chunks_count": len(relevant_chunks),
        "chunks_used": [
            {
                "content": chunk.page_content[:200] + "...",  # Preview
                "chunk_index": chunk.metadata.get('chunk_index'),
                "relevance_score": chunk.metadata.get('score', 'N/A')
            }
            for chunk in relevant_chunks
        ]
    }




    # all_documents = db.query(Document).filter(Document.user_id == current_user.id , Document.processing_status == "completed").all()
    # print(f"you have following documents \n {all_documents}")
    # doc_id = int(input("enter the id of the doc you want to chat with"))

    # doc =db.query(Document).filter(Document.file_id == doc_id).first()
    
    # vector_store = document_processor.get_vector_store(doc.collection_name)
    # all_chunks = vector_store.get() 



    



