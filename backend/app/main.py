from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import interview, health
from app.config import settings

app = FastAPI(
    title="AI Interviewer API",
    description="Backend API for AI-powered interview system",
    version="1.0.0"
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(interview.router, prefix="/api/interview", tags=["interview"])

@app.get("/")
async def root():
    return {"message": "AI Interviewer API is running!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)