"""Core Gmail management functionality."""

from .gmail_auth import GmailAuth
from .gmail_manager import GmailManager
from .email_processor import EmailProcessor, ProcessedEmail

__all__ = [
    "GmailAuth",
    "GmailManager", 
    "EmailProcessor",
    "ProcessedEmail",
]