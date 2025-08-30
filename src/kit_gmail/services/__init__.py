"""Services module for Kit Gmail."""

from .ai_service import AIService
from .contact_manager import ContactManager, Contact

__all__ = [
    "AIService",
    "ContactManager", 
    "Contact",
]