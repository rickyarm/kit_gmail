"""Integration tests for Gmail functionality."""

import pytest
from unittest.mock import Mock, patch
import asyncio

from kit_gmail.core import GmailManager
from kit_gmail.services import ContactManager


class TestGmailIntegration:
    
    @pytest.fixture
    def gmail_manager(self, mock_gmail_service):
        """GmailManager with mocked service."""
        manager = GmailManager()
        manager._service = mock_gmail_service
        return manager
    
    def test_get_messages(self, gmail_manager, mock_gmail_service):
        """Test message retrieval."""
        # Mock the API response
        mock_gmail_service.users().messages().list().execute.return_value = {
            "messages": [
                {"id": "msg1", "threadId": "thread1"},
                {"id": "msg2", "threadId": "thread2"}
            ]
        }
        
        messages = gmail_manager.get_messages(query="test", max_results=10)
        
        assert len(messages) == 2
        assert messages[0]["id"] == "msg1"
        assert messages[1]["id"] == "msg2"
    
    def test_get_message_details(self, gmail_manager, mock_gmail_service, sample_gmail_message):
        """Test detailed message retrieval."""
        mock_gmail_service.users().messages().get().execute.return_value = sample_gmail_message
        
        result = gmail_manager.get_message_details("test_message_id")
        
        assert result == sample_gmail_message
        mock_gmail_service.users().messages().get.assert_called_once_with(
            userId="me", id="test_message_id", format="full"
        )
    
    def test_batch_get_messages(self, gmail_manager, mock_gmail_service, sample_gmail_message):
        """Test batch message retrieval."""
        mock_gmail_service.users().messages().get().execute.return_value = sample_gmail_message
        
        message_ids = ["msg1", "msg2", "msg3"]
        results = gmail_manager.batch_get_messages(message_ids)
        
        assert len(results) == 3
        assert all(r == sample_gmail_message for r in results)
    
    def test_organize_message(self, gmail_manager, mock_gmail_service, sample_gmail_message):
        """Test message organization."""
        # Mock processed email
        processed_email = Mock()
        processed_email.is_receipt = True
        processed_email.is_mailing_list = False
        processed_email.is_critical = False
        processed_email.merchant = "Amazon"
        
        # Mock label operations
        mock_gmail_service.users().labels().list().execute.return_value = {
            "labels": [{"id": "receipts_id", "name": "Receipts"}]
        }
        mock_gmail_service.users().labels().create().execute.return_value = {
            "id": "new_label_id"
        }
        
        gmail_manager.organize_message(sample_gmail_message, processed_email)
        
        # Should attempt to modify message labels
        mock_gmail_service.users().messages().modify.assert_called_once()
    
    def test_delete_message(self, gmail_manager, mock_gmail_service):
        """Test message deletion."""
        gmail_manager.delete_message("test_message_id")
        
        mock_gmail_service.users().messages().delete.assert_called_once_with(
            userId="me", id="test_message_id"
        )
    
    def test_archive_message(self, gmail_manager, mock_gmail_service):
        """Test message archiving."""
        gmail_manager.archive_message("test_message_id")
        
        mock_gmail_service.users().messages().modify.assert_called_once_with(
            userId="me",
            id="test_message_id", 
            body={"removeLabelIds": ["INBOX"]}
        )
    
    def test_cleanup_mailbox_integration(self, gmail_manager, mock_gmail_service, sample_gmail_message):
        """Test full mailbox cleanup workflow."""
        # Mock message list
        mock_gmail_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg1", "threadId": "thread1"}]
        }
        
        # Mock message details
        mock_gmail_service.users().messages().get().execute.return_value = sample_gmail_message
        
        # Mock label operations
        mock_gmail_service.users().labels().list().execute.return_value = {"labels": []}
        
        stats = gmail_manager.cleanup_mailbox(days_old=30, delete_junk=True, archive_old=True)
        
        assert "processed" in stats
        assert "deleted" in stats
        assert "archived" in stats
        assert "organized" in stats
        
    def test_get_mailbox_stats(self, gmail_manager, mock_gmail_service):
        """Test mailbox statistics retrieval."""
        # Mock labels list
        mock_gmail_service.users().labels().list().execute.return_value = {
            "labels": [
                {"id": "INBOX", "name": "INBOX"},
                {"id": "SENT", "name": "SENT"}
            ]
        }
        
        # Mock label details
        mock_gmail_service.users().labels().get().execute.return_value = {
            "messagesTotal": 1000,
            "messagesUnread": 50,
            "threadsTotal": 800,
            "threadsUnread": 40
        }
        
        stats = gmail_manager.get_mailbox_stats()
        
        assert "INBOX" in stats
        assert "SENT" in stats
        assert stats["INBOX"]["messages_total"] == 1000
        assert stats["INBOX"]["messages_unread"] == 50


class TestContactIntegration:
    
    @pytest.fixture
    def contact_manager(self, temp_db_path):
        """ContactManager with temporary database."""
        return ContactManager(db_path=temp_db_path)
    
    def test_full_contact_analysis_workflow(self, contact_manager, sample_processed_email):
        """Test complete contact analysis workflow."""
        # Create multiple emails from different senders
        emails = []
        
        # Email from frequent sender
        for i in range(10):
            email = Mock(spec=sample_processed_email)
            email.sender = "frequent@example.com"
            email.sender_name = "Frequent Sender"
            email.recipients = ["me@example.com"]
            email.date = sample_processed_email.date
            email.subject = f"Email {i}"
            email.labels = ["INBOX"]
            email.is_junk = False
            email.is_automated = False
            emails.append(email)
        
        # Email from spam sender
        for i in range(5):
            email = Mock(spec=sample_processed_email)
            email.sender = "spam@marketing.com"
            email.sender_name = None
            email.recipients = ["me@example.com"]
            email.date = sample_processed_email.date
            email.subject = "PROMOTIONAL EMAIL!!!"
            email.labels = ["INBOX", "PROMOTIONS"]
            email.is_junk = True
            email.is_automated = True
            emails.append(email)
        
        # Analyze emails
        stats = contact_manager.analyze_emails(emails)
        
        assert stats["emails_processed"] == 15
        assert stats["new_contacts"] >= 2
        
        # Check contact classification
        contact_stats = contact_manager.get_contact_stats()
        assert contact_stats["total_contacts"] >= 2
        assert contact_stats["frequent_contacts"] >= 1
        assert contact_stats["spam_contacts"] >= 1
    
    def test_database_persistence(self, contact_manager, sample_contact):
        """Test contact database persistence."""
        # Add contact
        contact_manager.contacts[sample_contact.email] = sample_contact
        
        # Save to database
        contact_manager._save_contacts_to_db()
        
        # Create new manager instance and load
        new_manager = ContactManager(db_path=contact_manager.db_path)
        new_manager.load_contacts_from_db()
        
        # Verify contact was loaded
        assert len(new_manager.contacts) == 1
        loaded_contact = new_manager.contacts[sample_contact.email]
        assert loaded_contact.email == sample_contact.email
        assert loaded_contact.name == sample_contact.name
        assert loaded_contact.is_frequent == sample_contact.is_frequent


class TestEndToEndWorkflow:
    
    @pytest.fixture
    def full_setup(self, mock_gmail_service, temp_db_path):
        """Full application setup for end-to-end testing."""
        gmail_manager = GmailManager()
        gmail_manager._service = mock_gmail_service
        
        contact_manager = ContactManager(db_path=temp_db_path)
        
        return gmail_manager, contact_manager
    
    def test_complete_email_processing_workflow(self, full_setup, sample_gmail_message):
        """Test complete email processing from Gmail API to contact analysis."""
        gmail_manager, contact_manager = full_setup
        
        # Mock Gmail API responses
        gmail_manager._service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg1", "threadId": "thread1"}]
        }
        gmail_manager._service.users().messages().get().execute.return_value = sample_gmail_message
        
        # Fetch and process messages
        messages = gmail_manager.get_messages(max_results=10)
        message_details = gmail_manager.batch_get_messages([m["id"] for m in messages])
        
        # Process emails
        processed_emails = []
        for message in message_details:
            processed_email = gmail_manager.processor.process_email(message)
            processed_emails.append(processed_email)
        
        # Analyze contacts
        contact_stats = contact_manager.analyze_emails(processed_emails)
        
        # Verify workflow completed
        assert len(processed_emails) == 1
        assert contact_stats["emails_processed"] == 1
        assert contact_stats["new_contacts"] >= 1
        assert len(contact_manager.contacts) >= 1
    
    @pytest.mark.asyncio
    async def test_ai_summary_integration(self, full_setup, sample_gmail_message):
        """Test AI summary generation integration."""
        gmail_manager, _ = full_setup
        
        # Mock Gmail API responses
        gmail_manager._service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg1", "threadId": "thread1"}]
        }
        gmail_manager._service.users().messages().get().execute.return_value = sample_gmail_message
        
        # Mock AI service
        with patch.object(gmail_manager, 'ai_service') as mock_ai_service:
            mock_ai_service.get_provider.return_value = Mock()
            mock_ai_service.generate_email_summary = AsyncMock(return_value="Test summary")
            
            # Generate summary
            summary = await gmail_manager.generate_email_summary(days=7, summary_type="daily")
            
            assert summary == "Test summary"
            mock_ai_service.generate_email_summary.assert_called_once()