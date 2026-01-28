from db.db import get_db
from fastapi import Depends , HTTPException , status
from auth.auth import oauth2_scheme , verify_token
from datetime import datetime, date ,time
from decimal import Decimal
from uuid import UUID
from sqlalchemy.orm import Session
from models.models import RevokedTokens
from models.models import User

def model_to_dict(model_instance, exclude=None, relationship_depth=1, exclude_relationships=None):
    if model_instance is None:
        return None
    
    if exclude is None:
        exclude = []
    if exclude_relationships is None:
        exclude_relationships = []
    
    result = {}
    
    for column in model_instance.__table__.columns:
        col_name = column.name
        if col_name in exclude:
            continue
            
        value = getattr(model_instance, col_name)
        
        if value is None:
            result[col_name] = None
        elif isinstance(value, datetime):
            result[col_name] = value.isoformat()
        elif isinstance(value, date):
            result[col_name] = value.isoformat()
        elif isinstance(value, time):
            result[col_name] = value.isoformat()
        elif isinstance(value, Decimal):
            result[col_name] = float(value)
        elif isinstance(value, UUID):
            result[col_name] = str(value)
        else:
            result[col_name] = value
    
    if relationship_depth > 0:
        for rel_name, relationship in model_instance.__mapper__.relationships.items():
            if rel_name in exclude_relationships:
                continue
                
            related = getattr(model_instance, rel_name)
            
            if related is None:
                result[rel_name] = None
            elif isinstance(related, list):
                result[rel_name] = [
                    model_to_dict(
                        item,
                        exclude=exclude,
                        relationship_depth=relationship_depth - 1,
                        exclude_relationships=exclude_relationships
                    )
                    for item in related
                ]
            else:
                result[rel_name] = model_to_dict(
                    related,
                    exclude=exclude,
                    relationship_depth=relationship_depth - 1,
                    exclude_relationships=exclude_relationships
                )
    
    return result

def is_token_revoked(jti : int , db:Session):
    revoked_token = db.query(RevokedTokens).filter(RevokedTokens.jti == jti , RevokedTokens.expires_at > datetime.utcnow()).first()
    return revoked_token is not None

def revoke_token(jti: str, token_type: str, expires_at: datetime, user_id: int = None, db: Session = None):
    revoked_token = RevokedTokens(
        jti=jti,
        token_type=token_type,
        expires_at=expires_at,
        user_id=user_id
    )
    db.add(revoked_token)
    db.commit()



def get_current_user( token : str = Depends(oauth2_scheme) ,
        db : Session = Depends(get_db)):
    payload = verify_token(token)
    user_email = payload.get("email")
    user = db.query(User).filter(User.email == user_email).first()
    if not user :
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND , detail="no user found with this information"
        )
    return user