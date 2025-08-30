"""Pytest configuration and fixtures."""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timedelta
import os
import tempfile
from pathlib import Path

# Set up test environment
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["DEBUG"] = "true"


@pytest.fixture
def mock_gmail_service():
    """Mock Gmail API service."""
    service = Mock()
    
    # Mock users()
    service.users.return_value = Mock()
    service.users().getProfile.return_value.execute.return_value = {
        "emailAddress": "test@example.com",
        "messagesTotal": 1000,
        "threadsTotal": 800
    }
    
    # Mock messages
    service.users().messages.return_value = Mock()
    service.users().messages().list.return_value.execute.return_value = {
        "messages": [
            {"id": "msg1", "threadId": "thread1"},
            {"id": "msg2", "threadId": "thread2"}
        ]
    }
    
    # Mock labels
    service.users().labels.return_value = Mock()
    service.users().labels().list.return_value.execute.return_value = {
        "labels": [
            {"id": "INBOX", "name": "INBOX"},
            {"id": "SENT", "name": "SENT"}
        ]
    }
    
    return service


@pytest.fixture
def sample_gmail_message():
    """Sample Gmail API message."""
    return {
        "id": "test_message_id",
        "threadId": "test_thread_id",
        "labelIds": ["INBOX", "UNREAD"],
        "payload": {
            "headers": [
                {"name": "From", "value": "John Doe <john@example.com>"},
                {"name": "To", "value": "test@example.com"},
                {"name": "Subject", "value": "Test Email Subject"},
                {"name": "Date", "value": "Wed, 15 Nov 2023 10:30:00 +0000"},
            ],
            "mimeType": "text/plain",
            "body": {
                "data": "VGVzdCBlbWFpbCBib2R5IGNvbnRlbnQ="  # Base64: "Test email body content"
            }
        }
    }


@pytest.fixture
def sample_processed_email():
    """Sample processed email object."""
    from kit_gmail.core.email_processor import ProcessedEmail
    
    return ProcessedEmail(
        message_id="test_message_id",
        thread_id="test_thread_id",
        subject="Test Email Subject",
        sender="john@example.com",
        sender_name="John Doe",
        recipients=["test@example.com"],
        date=datetime.now(),
        body_text="Test email body content",
        labels=["INBOX", "UNREAD"]
    )


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client."""
    client = Mock()
    
    # Mock message creation
    mock_message = Mock()
    mock_message.content = [Mock(text="Test AI response")]
    client.messages.create.return_value = mock_message
    
    return client


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client."""
    client = Mock()
    
    # Mock chat completion
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="Test AI response"))]
    client.chat.completions.create.return_value = mock_response
    
    return client


@pytest.fixture
def temp_db_path():
    """Temporary database path for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        yield str(db_path)


@pytest.fixture
def mock_keyring():
    """Mock keyring for secure storage testing."""
    storage = {}
    
    def set_password(service, username, password):
        storage[f"{service}:{username}"] = password
        
    def get_password(service, username):
        return storage.get(f"{service}:{username}")
    
    def delete_password(service, username):
        key = f"{service}:{username}"
        if key in storage:
            del storage[key]
    
    with pytest.MonkeyPatch().context() as m:
        m.setattr("keyring.set_password", set_password)
        m.setattr("keyring.get_password", get_password) 
        m.setattr("keyring.delete_password", delete_password)
        yield storage


@pytest.fixture
def sample_contact():
    """Sample contact for testing."""
    from kit_gmail.services.contact_manager import Contact
    
    return Contact(
        email="john@example.com",
        name="John Doe",
        first_seen=datetime.now() - timedelta(days=30),
        last_seen=datetime.now() - timedelta(days=1),
        email_count=25,
        sent_count=5,
        received_count=20,
        is_frequent=True,
        confidence_score=0.8
    )


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset any singleton instances between tests."""
    # Clear any cached instances
    yield
    # Cleanup after test