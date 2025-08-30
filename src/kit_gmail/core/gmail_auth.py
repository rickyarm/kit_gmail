"""Gmail OAuth2 authentication management."""

import json
import os
from pathlib import Path
from typing import Optional

import keyring
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from ..utils.config import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.labels",
    "https://www.googleapis.com/auth/gmail.compose",
]


class GmailAuth:
    """Handles Gmail API authentication and credential management."""

    def __init__(self) -> None:
        self.credentials_file = Path.home() / ".kit_gmail" / "credentials.json"
        self.token_file = Path.home() / ".kit_gmail" / "token.json"
        self.credentials_file.parent.mkdir(exist_ok=True)
        self._creds: Optional[Credentials] = None

    def setup_credentials(self, credentials_json_path: str) -> None:
        """Copy OAuth2 credentials from Google Cloud Console to local storage."""
        import shutil
        
        if not Path(credentials_json_path).exists():
            raise FileNotFoundError(f"Credentials file not found: {credentials_json_path}")
        
        shutil.copy(credentials_json_path, self.credentials_file)
        logger.info(f"Credentials copied to {self.credentials_file}")

    def authenticate(self) -> Credentials:
        """Authenticate with Gmail API using OAuth2."""
        creds = None
        
        # Load existing token
        if self.token_file.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(self.token_file), SCOPES)
                logger.debug("Loaded existing credentials")
            except Exception as e:
                logger.warning(f"Failed to load existing credentials: {e}")

        # If credentials are not valid, refresh or re-authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info("Refreshed expired credentials")
                except Exception as e:
                    logger.warning(f"Failed to refresh credentials: {e}")
                    creds = None

            if not creds:
                # Run the OAuth flow
                if not self.credentials_file.exists():
                    raise FileNotFoundError(
                        f"Credentials file not found: {self.credentials_file}. "
                        "Please run 'kit-gmail auth setup' first."
                    )

                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_file), SCOPES
                )
                creds = flow.run_local_server(port=8080)
                logger.info("Completed OAuth2 authentication flow")

            # Save credentials for next run
            with open(self.token_file, "w") as token:
                token.write(creds.to_json())
            logger.info("Saved new credentials")

        self._creds = creds
        return creds

    def get_gmail_service(self):
        """Get authenticated Gmail API service."""
        if not self._creds:
            self.authenticate()
        
        service = build("gmail", "v1", credentials=self._creds)
        logger.debug("Created Gmail API service")
        return service

    def revoke_credentials(self) -> None:
        """Revoke and delete stored credentials."""
        if self._creds:
            try:
                self._creds.revoke(Request())
                logger.info("Revoked OAuth2 credentials")
            except Exception as e:
                logger.warning(f"Failed to revoke credentials: {e}")

        # Remove stored files
        for file_path in [self.token_file, self.credentials_file]:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted {file_path}")

        self._creds = None

    @property
    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated."""
        if not self._creds:
            if self.token_file.exists():
                try:
                    self._creds = Credentials.from_authorized_user_file(
                        str(self.token_file), SCOPES
                    )
                except Exception:
                    return False
            else:
                return False
        
        return self._creds.valid if self._creds else False