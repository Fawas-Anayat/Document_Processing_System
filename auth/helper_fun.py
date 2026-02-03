from db.db import get_db
from fastapi import Depends , HTTPException , status
from datetime import datetime, date ,time
from decimal import Decimal
from uuid import UUID
from sqlalchemy.orm import Session
from models.models import User
from groq import Groq
from config import settings

# def is_token_revoked(jti : int , db:Session):
#     revoked_token = db.query(User).filter(User == jti , RevokedTokens.expires_at > datetime.utcnow()).first()
#     return revoked_token is not None

# def revoke_token(jti: str, token_type: str, expires_at: datetime, user_id: int = None, db: Session = None):
#     revoked_token = RevokedTokens(
#         jti=jti,
#         token_type=token_type,
#         expires_at=expires_at,
#         user_id=user_id
#     )
#     db.add(revoked_token)
#     db.commit()

def chat_groq_model(query : str , context : str) -> str:
    client = Groq(api_key=settings.groq_api_key)
    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": f"Context: {context}\n\nQuestion: {query}"}
            ],
            temperature=0.7,
            max_tokens=1024,
            top_p=1,
            stream=False
        )
        answer = response.choices[0].message.content
        return answer
    except Exception as e:
        raise Exception(f"Groq API call failed: {str(e)}")

