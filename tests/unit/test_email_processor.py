"""Unit tests for EmailProcessor."""

import pytest
from datetime import datetime
from unittest.mock import patch

from kit_gmail.core.email_processor import EmailProcessor, ProcessedEmail


class TestEmailProcessor:
    
    def test_process_email_basic(self, sample_gmail_message):
        """Test basic email processing."""
        processor = EmailProcessor()
        result = processor.process_email(sample_gmail_message)
        
        assert isinstance(result, ProcessedEmail)
        assert result.message_id == "test_message_id"
        assert result.thread_id == "test_thread_id"
        assert result.subject == "Test Email Subject"
        assert result.sender == "john@example.com"
        assert result.sender_name == "John Doe"
        assert "test@example.com" in result.recipients
        assert result.body_text == "Test email body content"
        
    def test_extract_headers(self, sample_gmail_message):
        """Test header extraction."""
        processor = EmailProcessor()
        headers = processor._extract_headers(sample_gmail_message)
        
        assert headers["From"] == "John Doe <john@example.com>"
        assert headers["To"] == "test@example.com"
        assert headers["Subject"] == "Test Email Subject"
        
    def test_extract_sender_name(self):
        """Test sender name extraction."""
        processor = EmailProcessor()
        
        # With name
        name = processor._extract_sender_name("John Doe <john@example.com>")
        assert name == "John Doe"
        
        # Without name
        name = processor._extract_sender_name("john@example.com")
        assert name is None
        
        # With quotes
        name = processor._extract_sender_name('"John Doe" <john@example.com>')
        assert name == "John Doe"
        
    def test_parse_date(self):
        """Test date parsing."""
        processor = EmailProcessor()
        
        # Valid date
        date = processor._parse_date("Wed, 15 Nov 2023 10:30:00 +0000")
        assert isinstance(date, datetime)
        
        # Invalid date should return current time
        date = processor._parse_date("invalid date")
        assert isinstance(date, datetime)
        
    def test_calculate_junk_score(self, sample_processed_email):
        """Test junk score calculation."""
        processor = EmailProcessor()
        
        # Clean email
        content = "hello how are you today"
        score = processor._calculate_junk_score(sample_processed_email, content, {})
        assert score < 0.5
        
        # Junky email
        content = "URGENT SALE!!! Unsubscribe click here!!!"
        score = processor._calculate_junk_score(sample_processed_email, content, {})
        assert score > 0.5
        
    def test_calculate_receipt_score(self, sample_processed_email):
        """Test receipt score calculation."""
        processor = EmailProcessor()
        
        # Regular email
        content = "hello how are you today"
        score = processor._calculate_receipt_score(sample_processed_email, content)
        assert score < 0.3
        
        # Receipt-like email
        content = "Your order #12345 has been confirmed. Total: $29.99"
        score = processor._calculate_receipt_score(sample_processed_email, content)
        assert score > 0.6
        
    def test_detect_mailing_list(self):
        """Test mailing list detection."""
        processor = EmailProcessor()
        
        # With List-Id header
        headers = {"List-Id": "<newsletter@example.com>"}
        result = processor._detect_mailing_list(headers, "")
        assert result == "newsletter@example.com"
        
        # With List-Unsubscribe header
        headers = {"List-Unsubscribe": "<mailto:unsubscribe@newsletter.com>"}
        result = processor._detect_mailing_list(headers, "")
        assert result == "mailto:unsubscribe@newsletter.com"
        
        # Newsletter pattern in content
        headers = {}
        content = "This is our weekly newsletter digest"
        result = processor._detect_mailing_list(headers, content)
        assert result == "newsletter"
        
    def test_is_critical_sender(self):
        """Test critical sender detection."""
        processor = EmailProcessor()
        processor.critical_senders = {"bank", "government", "tax"}
        
        assert processor._is_critical_sender("noreply@bank.com")
        assert processor._is_critical_sender("alert@government.org") 
        assert not processor._is_critical_sender("marketing@store.com")
        
    def test_has_critical_keywords(self):
        """Test critical keyword detection."""
        processor = EmailProcessor()
        
        assert processor._has_critical_keywords("URGENT: Account suspended")
        assert processor._has_critical_keywords("Important security alert")
        assert processor._has_critical_keywords("Verify your account immediately")
        assert not processor._has_critical_keywords("Hello how are you")
        
    def test_is_automated_message(self):
        """Test automated message detection."""
        processor = EmailProcessor()
        
        # Header indicators
        headers = {"X-Auto-Response-Suppress": "OOF"}
        assert processor._is_automated_message(headers, "")
        
        headers = {"Auto-Submitted": "auto-generated"}
        assert processor._is_automated_message(headers, "")
        
        # Content indicators
        headers = {}
        assert processor._is_automated_message(headers, "Do not reply to this message")
        assert processor._is_automated_message(headers, "This is an automated message")
        assert not processor._is_automated_message(headers, "Please reply when convenient")
        
    def test_extract_merchant_name(self, sample_processed_email):
        """Test merchant name extraction."""
        processor = EmailProcessor()
        
        # From sender name
        sample_processed_email.sender_name = "Amazon Orders"
        result = processor._extract_merchant_name(sample_processed_email)
        assert result == "Amazon Orders"
        
        # From email domain
        sample_processed_email.sender_name = None
        sample_processed_email.sender = "orders@amazon.com"
        result = processor._extract_merchant_name(sample_processed_email)
        assert result == "Amazon"
        
    def test_extract_unsubscribe_link(self):
        """Test unsubscribe link extraction."""
        processor = EmailProcessor()
        
        # HTML with link
        html_content = '<a href="https://example.com/unsubscribe?id=123">Unsubscribe</a>'
        result = processor._extract_unsubscribe_link(html_content)
        assert "unsubscribe" in result.lower()
        
        # Plain text URL
        text_content = "To unsubscribe: https://example.com/unsubscribe"
        result = processor._extract_unsubscribe_link(text_content)
        assert "unsubscribe" in result.lower()
        
        # No unsubscribe link
        content = "Regular email content without unsubscribe"
        result = processor._extract_unsubscribe_link(content)
        assert result is None
        
    def test_classification_integration(self, sample_gmail_message):
        """Test complete email classification."""
        processor = EmailProcessor()
        
        # Modify message to be promotional
        sample_gmail_message["payload"]["headers"].append({
            "name": "Subject", 
            "value": "SALE: 50% OFF Everything! Unsubscribe here"
        })
        
        # Update body to be promotional
        import base64
        promo_body = "LIMITED TIME OFFER! 50% off sale! Click to unsubscribe"
        encoded_body = base64.urlsafe_b64encode(promo_body.encode()).decode()
        sample_gmail_message["payload"]["body"]["data"] = encoded_body
        
        result = processor.process_email(sample_gmail_message)
        
        assert result.is_promotional or result.is_junk  # Should be classified as promotional or junk
        assert result.confidence_score > 0.0