"""Unit tests for GmailAuth."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile

from kit_gmail.core.gmail_auth import GmailAuth


class TestGmailAuth:
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            with patch.object(Path, 'home', return_value=config_dir):
                yield config_dir / ".kit_gmail"
    
    @pytest.fixture 
    def gmail_auth(self, temp_config_dir):
        """GmailAuth instance with temporary config."""
        return GmailAuth()
    
    def test_init(self, gmail_auth, temp_config_dir):
        """Test GmailAuth initialization."""
        assert gmail_auth.credentials_file == temp_config_dir / "credentials.json"
        assert gmail_auth.token_file == temp_config_dir / "token.json"
        assert gmail_auth.credentials_file.parent.exists()
        
    def test_setup_credentials(self, gmail_auth, temp_config_dir):
        """Test credentials setup."""
        # Create a temporary source credentials file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"test": "credentials"}')
            source_path = f.name
        
        try:
            gmail_auth.setup_credentials(source_path)
            assert gmail_auth.credentials_file.exists()
            assert gmail_auth.credentials_file.read_text() == '{"test": "credentials"}'
        finally:
            Path(source_path).unlink()
    
    def test_setup_credentials_file_not_found(self, gmail_auth):
        """Test setup with non-existent credentials file."""
        with pytest.raises(FileNotFoundError):
            gmail_auth.setup_credentials("non_existent_file.json")
    
    @patch('kit_gmail.core.gmail_auth.Credentials')
    @patch('kit_gmail.core.gmail_auth.InstalledAppFlow')
    @patch('kit_gmail.core.gmail_auth.build')
    def test_authenticate_new_user(self, mock_build, mock_flow, mock_creds, gmail_auth):
        """Test authentication for new user."""
        # Setup mocks
        mock_credentials = Mock()
        mock_credentials.valid = True
        mock_credentials.to_json.return_value = '{"token": "test"}'
        
        mock_flow_instance = Mock()
        mock_flow_instance.run_local_server.return_value = mock_credentials
        mock_flow.from_client_secrets_file.return_value = mock_flow_instance
        
        # Create dummy credentials file
        gmail_auth.credentials_file.parent.mkdir(exist_ok=True)
        gmail_auth.credentials_file.write_text('{"client_id": "test"}')
        
        result = gmail_auth.authenticate()
        
        assert result == mock_credentials
        assert gmail_auth._creds == mock_credentials
        mock_flow.from_client_secrets_file.assert_called_once()
        mock_flow_instance.run_local_server.assert_called_once_with(port=8080)
    
    @patch('kit_gmail.core.gmail_auth.Credentials')
    def test_authenticate_existing_valid_token(self, mock_creds, gmail_auth):
        """Test authentication with existing valid token."""
        # Setup mock credentials
        mock_credentials = Mock()
        mock_credentials.valid = True
        mock_creds.from_authorized_user_file.return_value = mock_credentials
        
        # Create dummy token file
        gmail_auth.token_file.parent.mkdir(exist_ok=True)
        gmail_auth.token_file.write_text('{"token": "test"}')
        
        result = gmail_auth.authenticate()
        
        assert result == mock_credentials
        assert gmail_auth._creds == mock_credentials
        mock_creds.from_authorized_user_file.assert_called_once()
    
    @patch('kit_gmail.core.gmail_auth.Credentials')
    @patch('kit_gmail.core.gmail_auth.Request')
    def test_authenticate_refresh_expired_token(self, mock_request, mock_creds, gmail_auth):
        """Test authentication with expired but refreshable token."""
        # Setup mock credentials
        mock_credentials = Mock()
        mock_credentials.valid = False
        mock_credentials.expired = True
        mock_credentials.refresh_token = "refresh_token"
        mock_credentials.to_json.return_value = '{"token": "refreshed"}'
        mock_creds.from_authorized_user_file.return_value = mock_credentials
        
        # Mock refresh success
        def refresh_side_effect(request):
            mock_credentials.valid = True
        
        mock_credentials.refresh.side_effect = refresh_side_effect
        
        # Create dummy token file
        gmail_auth.token_file.parent.mkdir(exist_ok=True)
        gmail_auth.token_file.write_text('{"token": "expired"}')
        
        result = gmail_auth.authenticate()
        
        assert result == mock_credentials
        mock_credentials.refresh.assert_called_once()
    
    @patch('kit_gmail.core.gmail_auth.build')
    def test_get_gmail_service(self, mock_build, gmail_auth):
        """Test Gmail service creation."""
        # Setup mock credentials
        mock_credentials = Mock()
        gmail_auth._creds = mock_credentials
        
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        result = gmail_auth.get_gmail_service()
        
        assert result == mock_service
        mock_build.assert_called_once_with("gmail", "v1", credentials=mock_credentials)
    
    @patch('kit_gmail.core.gmail_auth.Request')
    def test_revoke_credentials(self, mock_request, gmail_auth):
        """Test credential revocation."""
        # Setup mock credentials
        mock_credentials = Mock()
        gmail_auth._creds = mock_credentials
        
        # Create dummy files
        gmail_auth.credentials_file.parent.mkdir(exist_ok=True)
        gmail_auth.credentials_file.write_text('{"test": "creds"}')
        gmail_auth.token_file.write_text('{"test": "token"}')
        
        gmail_auth.revoke_credentials()
        
        mock_credentials.revoke.assert_called_once()
        assert not gmail_auth.credentials_file.exists()
        assert not gmail_auth.token_file.exists()
        assert gmail_auth._creds is None
    
    def test_is_authenticated_no_token(self, gmail_auth):
        """Test authentication check with no token."""
        assert not gmail_auth.is_authenticated
    
    @patch('kit_gmail.core.gmail_auth.Credentials')
    def test_is_authenticated_valid_token(self, mock_creds, gmail_auth):
        """Test authentication check with valid token."""
        # Setup mock credentials
        mock_credentials = Mock()
        mock_credentials.valid = True
        mock_creds.from_authorized_user_file.return_value = mock_credentials
        
        # Create dummy token file
        gmail_auth.token_file.parent.mkdir(exist_ok=True)
        gmail_auth.token_file.write_text('{"token": "test"}')
        
        assert gmail_auth.is_authenticated
    
    @patch('kit_gmail.core.gmail_auth.Credentials')
    def test_is_authenticated_invalid_token(self, mock_creds, gmail_auth):
        """Test authentication check with invalid token."""
        # Setup mock credentials
        mock_credentials = Mock()
        mock_credentials.valid = False
        mock_creds.from_authorized_user_file.return_value = mock_credentials
        
        # Create dummy token file
        gmail_auth.token_file.parent.mkdir(exist_ok=True)
        gmail_auth.token_file.write_text('{"token": "test"}')
        
        assert not gmail_auth.is_authenticated