from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = "sqlite:///./ai_interviewer.db"
    
    # Azure (to be added later)
    AZURE_SPEECH_KEY: Optional[str] = None
    AZURE_SPEECH_REGION: Optional[str] = None
    AZURE_STORAGE_CONNECTION_STRING: Optional[str] = None
    
    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"
    
    class Config:
        env_file = ".env"

settings = Settings()