from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def health_check():
    
    return {
        "status": "healthy",
        "service": "AI Interviewer API",
        "version": "1.0.0"
    }

@router.get("/ready")
async def readiness_check():
    # TODO: Add checks for dependencies (Ollama, Azure, the rest)
    return {
        "status": "ready",
        "dependencies": {
            "ollama": "pending",
            "azure_speech": "pending"
        }
    }