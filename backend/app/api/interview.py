from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import io
from datetime import datetime, timedelta, timezone

from app.models.schemas import (
    InterviewSessionCreate, 
    InterviewSessionResponse,
    QuestionRequest,
    QuestionResponse, 
    AnswerSubmission,
    AnswerFeedback,
    InterviewDomains,
    FeedbackSpeechRequest
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
        print(f"Question request received for session {question_request.session_id}, context: {question_request.context}")
        
        # Get session details
        session = db.query(InterviewSession).filter(
            InterviewSession.id == question_request.session_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Check if interview time is up
        current_time = datetime.now(timezone.utc).replace(tzinfo=None)
        session_end_time = session.created_at + timedelta(minutes=session.duration_minutes)
        if session_end_time < current_time:
            if session.status != "completed":
                await complete_session(session.id, db)
            raise HTTPException(status_code=410, detail="Interview time has expired. Redirecting to results.")

        # Check existing questions for this session
        existing_questions = db.query(InterviewQuestion).filter(
            InterviewQuestion.session_id == question_request.session_id
        ).order_by(InterviewQuestion.id.asc()).all()
        
        print(f"Found {len(existing_questions)} existing questions for session {question_request.session_id}")
        
        # Logic for handling different scenarios
        if not question_request.context or question_request.context.strip() == "":
            # This is a request for the first question
            print("Request for first question (no context)")
            
            if existing_questions:
                # Return the first question that was already created
                first_question = existing_questions[0]
                print(f"Returning existing first question: {first_question.id}")
                return QuestionResponse(
                    id=first_question.id,
                    session_id=first_question.session_id,
                    question_text=first_question.question_text,
                    question_type="technical"
                )
            else:
                # No questions exist, create the first one
                print("No existing questions, creating first question")
        else:
            # This is a request with context (potentially for next question)
            print(f"Request with context: {question_request.context[:100]}...")
            
            if "Moving to next question" in question_request.context:
                # This is explicitly a request for the next question
                print("Explicit request for next question")
            else:
                # This might be a duplicate call or page refresh
                print("Potential duplicate call, checking for unanswered questions")
                
                # Find unanswered questions
                unanswered_questions = [q for q in existing_questions if q.user_answer is None]
                
                if unanswered_questions:
                    # Return the first unanswered question
                    unanswered_question = unanswered_questions[0]
                    print(f"Returning existing unanswered question: {unanswered_question.id}")
                    return QuestionResponse(
                        id=unanswered_question.id,
                        session_id=unanswered_question.session_id,
                        question_text=unanswered_question.question_text,
                        question_type="technical"
                    )
                # If all questions are answered, proceed to create a new one
        
        # If we reach here, we need to generate a new question
        print("Generating new question...")
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
        
        print(f"Created new question with ID: {db_question.id}")
        
        return QuestionResponse(
            id=db_question.id,
            session_id=db_question.session_id,
            question_text=db_question.question_text,
            question_type=question_data.get("question_type", "technical")
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 410 for expired session)
        raise
    except Exception as e:
        print(f"Error in get_next_question: {str(e)}")
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
        
        # Check if session is still active
        current_time = datetime.now(timezone.utc).replace(tzinfo=None)
        session_end_time = session.created_at + timedelta(minutes=session.duration_minutes)
        if session_end_time < current_time:
            if session.status != "completed":
                await complete_session(session.id, db)
            raise HTTPException(status_code=410, detail="Interview time has expired.")
        
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
        question.answered_at = datetime.now(timezone.utc).replace(tzinfo=None)
        
        db.commit()
        
        return AnswerFeedback(
            question_id=question_id,
            score=evaluation["score"],
            feedback=evaluation["feedback"],
            suggestions=evaluation.get("suggestions", [])
        )
        
    except HTTPException:
        raise
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
        # Check if question exists and session is still active
        question = db.query(InterviewQuestion).filter(
            InterviewQuestion.id == question_id
        ).first()
        
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")
            
        session = db.query(InterviewSession).filter(
            InterviewSession.id == question.session_id
        ).first()
        
        # Check if session is still active
        current_time = datetime.now(timezone.utc).replace(tzinfo=None)
        session_end_time = session.created_at + timedelta(minutes=session.duration_minutes)
        if session_end_time < current_time:
            if session.status != "completed":
                await complete_session(session.id, db)
            raise HTTPException(status_code=410, detail="Interview time has expired.")
        
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
        
    except HTTPException:
        raise
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

@router.post("/feedback/speech")
async def generate_feedback_speech(request: FeedbackSpeechRequest):
    """Generate speech audio for feedback text"""
    try:
        # Generate speech for the feedback text
        audio_data = await speech_service.text_to_speech(request.text)
        
        if not audio_data:
            return {"error": "Text-to-speech service not available"}
        
        # Return audio as streaming response
        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type="audio/wav",
            headers={"Content-Disposition": "attachment; filename=feedback_audio.wav"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating feedback audio: {str(e)}")

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
        session.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        
        db.commit()
        
        return {"message": "Session completed", "final_score": session.score}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error completing session: {str(e)}")

@router.get("/domains/{domain}/topics")
async def get_domain_topics(domain: str):
    """Get available topics for a specific domain"""
    try:
        # Check if domain exists in knowledge base
        if domain in rag_service.knowledge_base:
            # Get the sections/topics directly from the knowledge base
            domain_data = rag_service.knowledge_base[domain]
            sections = domain_data["sections"]
            
            # Extract just the section names (topics)
            topics = [section["section"] for section in sections if section["section"]]
            
            return {
                "domain": domain,
                "topics": topics,
                "total_topics": len(topics)
            }
        else:
            # Fallback: try to read the file directly
            from pathlib import Path
            topics_file = Path("app/data") / domain / "topics.md"
            if topics_file.exists():
                content = topics_file.read_text()
                
                # Extract section headings
                topics = []
                for line in content.split('\n'):
                    if line.startswith('## '):
                        topics.append(line[3:].strip())
                
                return {
                    "domain": domain,
                    "topics": topics,
                    "total_topics": len(topics)
                }
        
        # Final fallback
        return {
            "domain": domain,
            "topics": [f"General {domain} interview topics"],
            "total_topics": 1
        }
        
    except Exception as e:
        print(f"Error in get_domain_topics: {e}")
        return {
            "domain": domain,
            "topics": [f"General {domain} interview topics"],
            "total_topics": 1,
            "error": str(e)
        }

@router.get("/sessions/{session_id}/questions")
async def get_session_questions(session_id: int, db: Session = Depends(get_db)):
    """Get all questions for a session, ordered by creation time"""
    questions = db.query(InterviewQuestion).filter(
        InterviewQuestion.session_id == session_id
    ).order_by(InterviewQuestion.id.asc()).all()  # Order by ID to maintain creation order
    return questions