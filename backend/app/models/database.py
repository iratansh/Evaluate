from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from app.config import settings

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class InterviewSession(Base):
    __tablename__ = "interview_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String, nullable=False)  # Software Engineering, Data Science, etc.
    difficulty = Column(String, default="medium")  # easy, medium, hard
    duration_minutes = Column(Integer, default=45)
    status = Column(String, default="active")  # active, completed, abandoned
    score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

class InterviewQuestion(Base):
    __tablename__ = "interview_questions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, nullable=False)
    question_text = Column(Text, nullable=False)
    expected_answer = Column(Text, nullable=True)
    user_answer = Column(Text, nullable=True)
    score = Column(Float, nullable=True)
    feedback = Column(Text, nullable=True)
    asked_at = Column(DateTime, default=datetime.utcnow)
    answered_at = Column(DateTime, nullable=True)

# Create tables
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
