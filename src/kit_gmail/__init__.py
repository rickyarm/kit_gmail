"""
Kit Gmail - Knowledge Integration Tool for Gmail Management

A comprehensive Python application for intelligent Gmail mailbox management,
featuring AI-powered email summarization and advanced organization capabilities.
"""

__version__ = "0.1.0"
__author__ = "rickyarm"
__description__ = "Knowledge Integration Tool for Gmail Management"

from .core.gmail_manager import GmailManager
from .core.email_processor import EmailProcessor
from .services.ai_service import AIService

__all__ = [
    "GmailManager",
    "EmailProcessor", 
    "AIService",
]