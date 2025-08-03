from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import io

from app.models.schemas import (
    InterviewSessionCreate, 
    InterviewSessionResponse,
    QuestionRequest,
    QuestionResponse, 
    AnswerSubmission,
    AnswerFeedback,
    InterviewDomains
)
from app.models.database import get_db, InterviewSession, InterviewQuestion
from app.services.llm import llm_service
from app.services.speech import speech_service, storage_service
from app.services.rag import rag_service

router = APIRouter()

@router.get("/domains", response_model=InterviewDomains)
async def get_interview_domains():
    """Get available interview domains"""
    return InterviewDomains()

@router.post("/sessions", response_model=InterviewSessionResponse)
async def create_interview_session(
    session_data: InterviewSessionCreate,
    db: Session = Depends(get_db)
):
    """Create a new interview session"""
    try:
        db_session = InterviewSession(
            domain=session_data.domain,
            difficulty=session_data.difficulty,
            duration_minutes=session_data.duration_minutes
        )
        db.add(db_session)
        db.commit()
        db.refresh(db_session)
        
        return InterviewSessionResponse(
            id=db_session.id,
            domain=db_session.domain,
            difficulty=db_session.difficulty,
            duration_minutes=db_session.duration_minutes,
            status=db_session.status,
            score=db_session.score,
            created_at=db_session.created_at,
            completed_at=db_session.completed_at
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating session: {str(e)}")

@router.get("/sessions/{session_id}", response_model=InterviewSessionResponse)
async def get_interview_session(session_id: int, db: Session = Depends(get_db)):
    """Get interview session details"""
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return InterviewSessionResponse(
        id=session.id,
        domain=session.domain,
        difficulty=session.difficulty,
        duration_minutes=session.duration_minutes,
        status=session.status,
        score=session.score,
        created_at=session.created_at,
        completed_at=session.completed_at
    )

@router.post("/questions", response_model=QuestionResponse)
async def get_next_question(
    question_request: QuestionRequest,
    db: Session = Depends(get_db)
):
    """Generate next interview question"""
    try:
        # Get session details
        session = db.query(InterviewSession).filter(
            InterviewSession.id == question_request.session_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Generate question using LLM
        question_data = await llm_service.generate_question(
            domain=session.domain,
            difficulty=session.difficulty,
            context=question_request.context
        )
        
        # Save question to database
        db_question = InterviewQuestion(
            session_id=question_request.session_id,
            question_text=question_data["question_text"],
            expected_answer=str(question_data.get("expected_concepts", []))
        )
        db.add(db_question)
        db.commit()
        db.refresh(db_question)
        
        return QuestionResponse(
            id=db_question.id,
            session_id=db_question.session_id,
            question_text=db_question.question_text,
            question_type=question_data.get("question_type", "technical")
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating question: {str(e)}")

@router.post("/questions/{question_id}/answer", response_model=AnswerFeedback)
async def submit_answer(
    question_id: int,
    answer: AnswerSubmission,
    db: Session = Depends(get_db)
):
    """Submit answer and get feedback"""
    try:
        # Get question
        question = db.query(InterviewQuestion).filter(
            InterviewQuestion.id == question_id
        ).first()
        
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")
        
        # Get session for domain context
        session = db.query(InterviewSession).filter(
            InterviewSession.id == question.session_id
        ).first()
        
        # Evaluate answer using LLM
        evaluation = await llm_service.evaluate_answer(
            question=question.question_text,
            answer=answer.answer_text,
            domain=session.domain
        )
        
        # Update question with answer and feedback
        question.user_answer = answer.answer_text
        question.score = evaluation["score"]
        question.feedback = evaluation["feedback"]
        
        db.commit()
        
        return AnswerFeedback(
            question_id=question_id,
            score=evaluation["score"],
            feedback=evaluation["feedback"],
            suggestions=evaluation.get("suggestions", [])
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing answer: {str(e)}")

@router.post("/questions/{question_id}/audio")
async def submit_audio_answer(
    question_id: int,
    audio_file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Submit audio answer and convert to text"""
    try:
        # Read audio file
        audio_data = await audio_file.read()
        
        # Convert speech to text
        transcribed_text = await speech_service.speech_to_text(audio_data)
        
        # Check if transcription failed or is empty
        if not transcribed_text or transcribed_text in [
            "Speech recognition not available. Please type your answer.",
            "Could not understand the audio. Please try again.",
            "Speech recognition was cancelled. Please try again.",
            "Speech recognition failed. Please type your answer.",
            "Speech recognition error. Please type your answer."
        ]:
            # Return error response instead of evaluating
            return {
                "question_id": question_id,
                "score": 0,
                "feedback": "No speech detected in the audio. Please ensure you're speaking clearly into the microphone.",
                "suggestions": [
                    "Make sure your microphone is working properly",
                    "Speak clearly and at a normal pace",
                    "Try recording again or type your answer instead"
                ],
                "error": True
            }
        
        # Check if the transcribed text is too short (likely silence)
        if len(transcribed_text.strip()) < 10:
            return {
                "question_id": question_id,
                "score": 0,
                "feedback": f"Answer too short: '{transcribed_text}'. Please provide a more detailed response.",
                "suggestions": [
                    "Elaborate on your answer with examples",
                    "Explain your reasoning",
                    "Consider the key concepts related to the question"
                ],
                "error": True
            }
        
        # Upload audio file
        audio_url = await storage_service.upload_audio(audio_data)
        
        # Submit as text answer
        answer_submission = AnswerSubmission(
            question_id=question_id,
            answer_text=transcribed_text,
            answer_audio_url=audio_url
        )
        
        return await submit_answer(question_id, answer_submission, db)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing audio: {str(e)}")

@router.get("/questions/{question_id}/speech")
async def get_question_audio(question_id: int, db: Session = Depends(get_db)):
    """Get question as audio"""
    try:
        question = db.query(InterviewQuestion).filter(
            InterviewQuestion.id == question_id
        ).first()
        
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")
        
        # Convert question to speech
        audio_data = await speech_service.text_to_speech(question.question_text)
        
        if not audio_data:
            # Return a JSON response indicating TTS is not available instead of 500 error
            return {"error": "Text-to-speech not available", "question_text": question.question_text}
        
        # Return audio as streaming response
        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type="audio/wav",
            headers={"Content-Disposition": f"attachment; filename=question_{question_id}.wav"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating audio: {str(e)}")

@router.put("/sessions/{session_id}/complete")
async def complete_session(session_id: int, db: Session = Depends(get_db)):
    """Mark session as completed and calculate final score"""
    try:
        session = db.query(InterviewSession).filter(
            InterviewSession.id == session_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Calculate average score from all questions
        questions = db.query(InterviewQuestion).filter(
            InterviewQuestion.session_id == session_id,
            InterviewQuestion.score.isnot(None)
        ).all()
        
        if questions:
            avg_score = sum(q.score for q in questions) / len(questions)
            session.score = round(avg_score, 2)
        
        session.status = "completed"
        from datetime import datetime
        session.completed_at = datetime.utcnow()
        
        db.commit()
        
        return {"message": "Session completed", "final_score": session.score}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error completing session: {str(e)}")

@router.get("/domains/{domain}/topics")
async def get_domain_topics(domain: str):
    """Get available topics for a specific domain"""
    try:
        # Get relevant context/topics for the domain
        topics = await rag_service.get_relevant_context(
            query=f"{domain} interview topics", 
            domain=domain, 
            n_results=10
        )
        
        return {
            "domain": domain,
            "topics": topics,
            "total_topics": len(topics)
        }
    except Exception as e:
        return {
            "domain": domain,
            "topics": [f"General {domain} interview topics"],
            "total_topics": 1,
            "error": str(e)
        }

@router.get("/sessions/{session_id}/questions")
async def get_session_questions(session_id: int, db: Session = Depends(get_db)):
    questions = db.query(InterviewQuestion).filter(
        InterviewQuestion.session_id == session_id
    ).all()
    return questions