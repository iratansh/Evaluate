from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class InterviewSessionCreate(BaseModel):
    domain: str
    difficulty: str = "medium"
    duration_minutes: int = 45

class InterviewSessionResponse(BaseModel):
    id: int
    domain: str
    difficulty: str
    duration_minutes: int
    status: str
    score: Optional[float] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

class QuestionRequest(BaseModel):
    session_id: int
    context: Optional[str] = None  # Previous conversation context

class QuestionResponse(BaseModel):
    id: int
    session_id: int
    question_text: str
    question_type: str  # technical, behavioral, coding
    
class AnswerSubmission(BaseModel):
    question_id: int
    answer_text: str
    answer_audio_url: Optional[str] = None

class AnswerFeedback(BaseModel):
    question_id: int
    score: float  # 0-10 scale
    feedback: str
    suggestions: List[str]

class InterviewDomains(BaseModel):
    domains: List[str] = [
        "Software Engineering",
        "Data Science", 
        "AI/ML",
        "Hardware/ECE",
        "Robotics"
    ]

class FeedbackSpeechRequest(BaseModel):
    text: str
