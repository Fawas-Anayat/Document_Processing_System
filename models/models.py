from sqlalchemy.orm import Mapped , mapped_column , relationship
from sqlalchemy import ForeignKey
from db.db import Base
from datetime import datetime , timedelta
from typing import Optional

class User(Base):

    __tablename__ = "users"

    id : Mapped[int] = mapped_column(primary_key=True)
    name : Mapped[str] = mapped_column(nullable=False)
    email : Mapped[str] = mapped_column(unique=True)
    hashed_password : Mapped[str] = mapped_column()
    created_at : Mapped[datetime] = mapped_column(default=datetime.utcnow())
    is_active : Mapped[bool] = mapped_column(nullable=True)
    is_verified : Mapped[bool] = mapped_column(nullable=True)


    documents = relationship("Document" , back_populates="user" , cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken" , back_populates="user" , cascade="all, delete-orphan")
    blacklisted_tokens = relationship("BlacklistedAccessTokens" , back_populates="user" , cascade="all , delete-orphan")

class Document(Base):

    __tablename__ = "documents" 
    
    file_id : Mapped[int] = mapped_column(primary_key=True)
    user_id : Mapped[int] = mapped_column(ForeignKey("users.id"))
    file_size : Mapped[str] = mapped_column()
    file_path : Mapped[str] = mapped_column()
    upload_time : Mapped[datetime] = mapped_column(default=datetime.utcnow())

    user = relationship("User" , back_populates = "documents")

class RefreshToken(Base):

    __tablename__ ="refresh_tokens"

    token_id :Mapped[int] = mapped_column(primary_key=True)
    token :Mapped[str] = mapped_column(unique=True , nullable=False)
    jti : Mapped[str] = mapped_column(unique=True)
    user_id : Mapped[int] = mapped_column(ForeignKey("users.id") , nullable=False)
    created_at :Mapped[datetime] = mapped_column(nullable=False)
    expires_at :Mapped[datetime] = mapped_column(nullable=False)
    is_revoked: Mapped[bool] = mapped_column(default=False)



    user = relationship("User" , back_populates="refresh_tokens")

    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)

class BlacklistedAccessTokens(Base):

    __tablename__ = "blacklisted_access_tokens"

    id : Mapped[int] = mapped_column(primary_key=True)
    user_id :Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    jti : Mapped[str] = mapped_column(nullable=False , unique=True)
    blacklisted_at : Mapped[datetime] = mapped_column(default=datetime.utcnow())
    expires_at : Mapped[datetime] = mapped_column(nullable=False)

    user = relationship("User" , back_populates= "blacklisted_tokens")




    



