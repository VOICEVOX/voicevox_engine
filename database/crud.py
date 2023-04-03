from sqlalchemy.orm import Session
from database.dbconnect import SessionLocal, engine
from auth.schemas import (
    UserAuth,
    ConversationCreate,
    MessageCreate
)
from database import models
from auth.utils import (
    get_hashed_password,
    payload_token
)


models.Base.metadata.create_all(bind=engine)

# User
def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

def create_user(db: Session, user: UserAuth):
    hashed_password = get_hashed_password(user.password)
    db_user = models.User(email=user.email, password=hashed_password, username = user.username)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user_by_token(db: Session, token: str):
    payload = payload_token(token=token)
    return get_user_by_email(db, payload['sub'])

# Conversation
def get_conversations(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Conversation).offset(skip).limit(limit).all()

def get_conversations_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Conversation).filter(models.Conversation.user_id == user_id).offset(skip).limit(limit).all()

def create_conversation(db: Session, conv: ConversationCreate):
    db_conv = models.Conversation(user_id = conv.user_id)
    db.add(db_conv)
    db.commit()
    db.refresh(db_conv)
    return db_conv

# Message
def create_message(db: Session, message: MessageCreate):
    db_message = models.Message(request=message.request, response=message.response, conversation_id=message.conversation_id)
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message

def get_messages_by_conversation(db: Session, conversation_id: int):
    return db.query(models.Message).filter(models.Message.conversation_id==conversation_id).all()

