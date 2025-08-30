"""Configuration management using Pydantic Settings."""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Gmail API Configuration
    gmail_client_id: Optional[str] = None
    gmail_client_secret: Optional[str] = None
    gmail_redirect_uri: str = "http://localhost:8080"
    
    # AI Service Configuration
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    xai_api_key: Optional[str] = None
    default_ai_service: str = "anthropic"
    
    # Database Configuration
    database_url: str = "sqlite:///kit_gmail.db"
    
    # Application Settings
    debug: bool = False
    log_level: str = "INFO"
    max_email_batch_size: int = 100
    default_summary_days: int = 7
    
    # Security
    secret_key: Optional[str] = None
    
    # Email Processing Settings
    receipt_keywords: str = "receipt,invoice,order,purchase,payment"
    junk_keywords: str = "unsubscribe,promotion,deal,offer,sale"
    critical_senders: str = "bank,insurance,government,tax"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()