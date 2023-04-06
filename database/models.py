from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database.dbconnect import Base

class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, index=True, )
    username = Column(String(100), unique=True, index=True)
    password = Column(String(200))
    is_active = Column(Boolean, default=True)
    access_token = Column(String(200), nullable=True)
    refresh_token = Column(String(200), nullable=True)

    conversations = relationship('Conversation', backref='user', lazy=True)

class Conversation(Base):
    __tablename__ = "conversation"

    id = Column(Integer, primary_key=True, index=True)
    start_date = Column(DateTime, default=datetime.now())
    finish_date = Column(DateTime, nullable=True)
    messages = relationship('Message', backref='conversation', lazy=True)
    user_id = Column(Integer, ForeignKey('user.id'))

class Message(Base):
    __tablename__ = "message"

    id = Column(Integer, primary_key=True, index=True)
    request = Column(String(500), nullable=True)
    response = Column(String(500), nullable=True)
    created_date = Column(DateTime, default=datetime.now())

    conversation_id = Column(Integer, ForeignKey('conversation.id'))