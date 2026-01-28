from sqlalchemy.orm import Mapped , mapped_column , relationship
from sqlalchemy import ForeignKey
from db.db import Base
from datetime import datetime , timedelta

class User(Base):

    __tablename__ = "users"

    id : Mapped[int] = mapped_column(primary_key=True)
    name : Mapped[str] = mapped_column(nullable=False)
    email : Mapped[str] = mapped_column(unique=True)
    hashed_password : Mapped[str] = mapped_column()

    documents = relationship("Document" , back_populates="user" , cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken" , back_populates="user" , cascade="all, delete-orphan")

class Document(Base):

    __tablename__ = "documents" 
    
    file_id : Mapped[int] = mapped_column(primary_key=True)
    user_id : Mapped[int] = mapped_column(ForeignKey("users.id"))
    file_size : Mapped[str] = mapped_column()
    file_path : Mapped[str] = mapped_column()
    upload_time : Mapped[datetime] = mapped_column()

    user = relationship("User" , back_populates = "documents")

class RefreshToken(Base):

    __tablename__ ="refresh_tokens"

    token_id :Mapped[int] = mapped_column(primary_key=True)
    token :Mapped[str] = mapped_column(unique=True , nullable=False)
    user_id : Mapped[int] = mapped_column(ForeignKey("users.id") , nullable=False)
    created_at :Mapped[int] = mapped_column(nullable=False)
    expires_at :Mapped[int] = mapped_column(nullable=False)

    user = relationship("User" , back_populates="refresh_tokens")


