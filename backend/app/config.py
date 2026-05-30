from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Security
    api_key: str
    
    # Model Configuration
    wakeword_model: str = "jarvis"
    threshold: float = 0.5
    debounce_frames: int = 15
    
    # Logging
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
