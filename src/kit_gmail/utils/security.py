"""Security utilities and helpers."""

import hashlib
import secrets
from pathlib import Path
from typing import Optional
import keyring

from .logger import get_logger

logger = get_logger(__name__)

SERVICE_NAME = "kit-gmail"


def generate_secret_key(length: int = 32) -> str:
    """Generate a cryptographically secure secret key."""
    return secrets.token_urlsafe(length)


def hash_email(email: str) -> str:
    """Hash email address for privacy in logs."""
    return hashlib.sha256(email.encode()).hexdigest()[:8]


def store_api_key(service: str, api_key: str) -> bool:
    """Securely store API key using keyring."""
    try:
        keyring.set_password(SERVICE_NAME, service, api_key)
        logger.info(f"Stored API key for {service}")
        return True
    except Exception as e:
        logger.error(f"Failed to store API key for {service}: {e}")
        return False


def retrieve_api_key(service: str) -> Optional[str]:
    """Retrieve API key from secure storage."""
    try:
        api_key = keyring.get_password(SERVICE_NAME, service)
        if api_key:
            logger.debug(f"Retrieved API key for {service}")
        return api_key
    except Exception as e:
        logger.error(f"Failed to retrieve API key for {service}: {e}")
        return None


def delete_api_key(service: str) -> bool:
    """Delete API key from secure storage."""
    try:
        keyring.delete_password(SERVICE_NAME, service)
        logger.info(f"Deleted API key for {service}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete API key for {service}: {e}")
        return False


def validate_email_address(email: str) -> bool:
    """Basic email address validation."""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal."""
    # Remove path separators and dangerous characters
    sanitized = "".join(c for c in filename if c.isalnum() or c in "._-")
    # Limit length
    return sanitized[:255]


def is_safe_url(url: str) -> bool:
    """Check if URL is safe (basic validation)."""
    from urllib.parse import urlparse
    
    try:
        parsed = urlparse(url)
        # Only allow http/https
        if parsed.scheme not in ['http', 'https']:
            return False
        # Require hostname
        if not parsed.hostname:
            return False
        # Block localhost and private IPs (basic check)
        if parsed.hostname in ['localhost', '127.0.0.1', '0.0.0.0']:
            return False
        return True
    except Exception:
        return False


class SecureConfig:
    """Secure configuration manager with keyring integration."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path.home() / ".kit_gmail"
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def set_secure_value(self, key: str, value: str) -> bool:
        """Store a value securely in keyring."""
        return store_api_key(key, value)
    
    def get_secure_value(self, key: str) -> Optional[str]:
        """Retrieve a value from secure storage."""
        return retrieve_api_key(key)
    
    def delete_secure_value(self, key: str) -> bool:
        """Delete a value from secure storage."""
        return delete_api_key(key)
    
    def list_secure_keys(self) -> list:
        """List available secure keys (implementation depends on keyring backend)."""
        # This is a simplified implementation
        # Real implementation would depend on the keyring backend
        common_keys = [
            "anthropic_api_key",
            "openai_api_key", 
            "xai_api_key",
            "gmail_client_id",
            "gmail_client_secret"
        ]
        
        available_keys = []
        for key in common_keys:
            if self.get_secure_value(key):
                available_keys.append(key)
        
        return available_keys