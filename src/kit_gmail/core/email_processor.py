"""Email processing and classification functionality."""

import base64
import email
import re
from datetime import datetime
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field

import dateparser
from email_validator import validate_email, EmailNotValidError

from ..utils.config import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ProcessedEmail:
    """Structured representation of a processed email."""
    
    message_id: str
    thread_id: str
    subject: str
    sender: str
    sender_name: Optional[str]
    recipients: List[str]
    date: datetime
    body_text: str
    body_html: Optional[str] = None
    attachments: List[Dict] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)
    
    # Classification flags
    is_junk: bool = False
    is_critical: bool = False
    is_receipt: bool = False
    is_mailing_list: bool = False
    is_promotional: bool = False
    is_social: bool = False
    is_automated: bool = False
    
    # Additional metadata
    merchant: Optional[str] = None
    list_name: Optional[str] = None
    unsubscribe_link: Optional[str] = None
    confidence_score: float = 0.0
    processing_notes: List[str] = field(default_factory=list)


class EmailProcessor:
    """Processes and classifies emails for organization and management."""

    def __init__(self) -> None:
        self.receipt_keywords = self._parse_keywords(settings.receipt_keywords)
        self.junk_keywords = self._parse_keywords(settings.junk_keywords)
        self.critical_senders = self._parse_keywords(settings.critical_senders)
        
        # Compiled regex patterns for better performance
        self.unsubscribe_pattern = re.compile(
            r'unsubscribe|opt.?out|remove.*list', re.IGNORECASE
        )
        self.receipt_pattern = re.compile(
            r'receipt|invoice|order\s*#|purchase|payment|confirmation', re.IGNORECASE
        )
        self.promotional_pattern = re.compile(
            r'sale|deal|offer|discount|promotion|coupon|special', re.IGNORECASE
        )

    def _parse_keywords(self, keyword_string: str) -> Set[str]:
        """Parse comma-separated keywords into a set."""
        if not keyword_string:
            return set()
        return {kw.strip().lower() for kw in keyword_string.split(',')}

    def process_email(self, message: Dict) -> ProcessedEmail:
        """Process a Gmail API message into a structured format."""
        try:
            # Extract basic message info
            headers = self._extract_headers(message)
            subject = headers.get('Subject', '')
            sender = headers.get('From', '')
            sender_name = self._extract_sender_name(sender)
            recipients = self._extract_recipients(headers)
            date = self._parse_date(headers.get('Date', ''))
            
            # Extract message body
            body_text, body_html = self._extract_body(message)
            
            # Extract attachments
            attachments = self._extract_attachments(message)
            
            # Get labels
            labels = message.get('labelIds', [])
            
            # Create processed email object
            processed_email = ProcessedEmail(
                message_id=message['id'],
                thread_id=message['threadId'],
                subject=subject,
                sender=sender,
                sender_name=sender_name,
                recipients=recipients,
                date=date,
                body_text=body_text,
                body_html=body_html,
                attachments=attachments,
                labels=labels,
            )
            
            # Perform classification
            self._classify_email(processed_email, headers)
            
            logger.debug(f"Processed email: {subject[:50]}...")
            return processed_email
            
        except Exception as e:
            logger.error(f"Failed to process email {message.get('id', 'unknown')}: {e}")
            raise

    def _extract_headers(self, message: Dict) -> Dict[str, str]:
        """Extract email headers into a dictionary."""
        headers = {}
        payload = message.get('payload', {})
        
        for header in payload.get('headers', []):
            headers[header['name']] = header['value']
        
        return headers

    def _extract_sender_name(self, from_header: str) -> Optional[str]:
        """Extract sender name from From header."""
        if not from_header:
            return None
            
        # Parse format: "Name <email@domain.com>" or just "email@domain.com"
        match = re.match(r'^(.+?)\s*<(.+)>$', from_header)
        if match:
            name = match.group(1).strip(' "')
            return name if name else None
        return None

    def _extract_recipients(self, headers: Dict[str, str]) -> List[str]:
        """Extract recipient email addresses."""
        recipients = []
        
        for header_name in ['To', 'Cc', 'Bcc']:
            if header_name in headers:
                recipients.extend(self._parse_email_list(headers[header_name]))
        
        return recipients

    def _parse_email_list(self, email_string: str) -> List[str]:
        """Parse comma-separated email addresses."""
        emails = []
        
        for email_part in email_string.split(','):
            email_part = email_part.strip()
            
            # Extract email from "Name <email>" format
            match = re.search(r'<(.+?)>', email_part)
            if match:
                email_addr = match.group(1)
            else:
                email_addr = email_part
            
            try:
                validated = validate_email(email_addr)
                emails.append(validated.email)
            except EmailNotValidError:
                logger.debug(f"Invalid email address: {email_addr}")
                continue
                
        return emails

    def _parse_date(self, date_string: str) -> datetime:
        """Parse email date string into datetime object."""
        if not date_string:
            return datetime.now()
            
        try:
            parsed_date = dateparser.parse(date_string)
            return parsed_date if parsed_date else datetime.now()
        except Exception as e:
            logger.warning(f"Failed to parse date '{date_string}': {e}")
            return datetime.now()

    def _extract_body(self, message: Dict) -> tuple[str, Optional[str]]:
        """Extract text and HTML body from message."""
        payload = message.get('payload', {})
        body_text = ""
        body_html = None
        
        def extract_from_part(part):
            nonlocal body_text, body_html
            
            mime_type = part.get('mimeType', '')
            body = part.get('body', {})
            
            if mime_type == 'text/plain' and 'data' in body:
                text_data = base64.urlsafe_b64decode(body['data']).decode('utf-8')
                body_text += text_data
                
            elif mime_type == 'text/html' and 'data' in body:
                html_data = base64.urlsafe_b64decode(body['data']).decode('utf-8')
                if not body_html:
                    body_html = html_data
                    
        # Handle multipart messages
        if 'parts' in payload:
            for part in payload['parts']:
                if 'parts' in part:  # Nested multipart
                    for subpart in part['parts']:
                        extract_from_part(subpart)
                else:
                    extract_from_part(part)
        else:
            extract_from_part(payload)
            
        return body_text.strip(), body_html

    def _extract_attachments(self, message: Dict) -> List[Dict]:
        """Extract attachment information."""
        attachments = []
        payload = message.get('payload', {})
        
        def process_part(part):
            if part.get('filename'):
                attachment = {
                    'filename': part['filename'],
                    'mime_type': part.get('mimeType', ''),
                    'size': part.get('body', {}).get('size', 0),
                    'attachment_id': part.get('body', {}).get('attachmentId'),
                }
                attachments.append(attachment)
                
        if 'parts' in payload:
            for part in payload['parts']:
                if 'parts' in part:
                    for subpart in part['parts']:
                        process_part(subpart)
                else:
                    process_part(part)
        else:
            process_part(payload)
            
        return attachments

    def _classify_email(self, email: ProcessedEmail, headers: Dict[str, str]) -> None:
        """Classify email based on content and metadata."""
        content = f"{email.subject} {email.body_text}".lower()
        sender_lower = email.sender.lower()
        
        confidence_factors = []
        
        # Check for junk/promotional content
        junk_score = self._calculate_junk_score(email, content, headers)
        if junk_score > 0.7:
            email.is_junk = True
            confidence_factors.append(f"junk_score: {junk_score:.2f}")
        
        # Check for promotional content
        if self.promotional_pattern.search(content) or 'promotion' in email.labels:
            email.is_promotional = True
            confidence_factors.append("promotional_pattern")
        
        # Check for receipts/invoices
        receipt_score = self._calculate_receipt_score(email, content)
        if receipt_score > 0.6:
            email.is_receipt = True
            email.merchant = self._extract_merchant_name(email)
            confidence_factors.append(f"receipt_score: {receipt_score:.2f}")
        
        # Check for mailing lists
        list_info = self._detect_mailing_list(headers, content)
        if list_info:
            email.is_mailing_list = True
            email.list_name = list_info
            confidence_factors.append(f"mailing_list: {list_info}")
        
        # Check for critical emails
        if self._is_critical_sender(sender_lower) or self._has_critical_keywords(content):
            email.is_critical = True
            confidence_factors.append("critical_sender_or_keywords")
        
        # Check for automated messages
        if self._is_automated_message(headers, content):
            email.is_automated = True
            confidence_factors.append("automated_message")
        
        # Extract unsubscribe link
        unsubscribe_link = self._extract_unsubscribe_link(email.body_html or email.body_text)
        if unsubscribe_link:
            email.unsubscribe_link = unsubscribe_link
        
        # Calculate overall confidence score
        email.confidence_score = min(1.0, len(confidence_factors) * 0.2)
        email.processing_notes = confidence_factors

    def _calculate_junk_score(self, email: ProcessedEmail, content: str, headers: Dict) -> float:
        """Calculate probability that email is junk."""
        score = 0.0
        
        # Check for junk keywords
        junk_matches = sum(1 for keyword in self.junk_keywords if keyword in content)
        score += min(0.5, junk_matches * 0.1)
        
        # Check for promotional patterns
        if self.promotional_pattern.search(content):
            score += 0.3
        
        # Check for unsubscribe links
        if self.unsubscribe_pattern.search(content):
            score += 0.2
        
        # Check for excessive capitalization
        if content.count('!') > 3:
            score += 0.1
        
        # Check sender reputation (simplified)
        sender_domain = email.sender.split('@')[-1].lower()
        if any(spam_indicator in sender_domain for spam_indicator in ['noreply', 'marketing', 'promo']):
            score += 0.2
        
        return min(1.0, score)

    def _calculate_receipt_score(self, email: ProcessedEmail, content: str) -> float:
        """Calculate probability that email is a receipt/invoice."""
        score = 0.0
        
        # Check for receipt keywords
        receipt_matches = sum(1 for keyword in self.receipt_keywords if keyword in content)
        score += min(0.6, receipt_matches * 0.2)
        
        # Check for receipt patterns
        if self.receipt_pattern.search(content):
            score += 0.3
        
        # Check for monetary amounts
        money_pattern = re.compile(r'\$\d+\.\d{2}|\d+\.\d{2}\s*(usd|eur|gbp)', re.IGNORECASE)
        if money_pattern.search(content):
            score += 0.2
        
        # Check for order numbers
        order_pattern = re.compile(r'order\s*#?\s*\d+|confirmation\s*#?\s*\d+', re.IGNORECASE)
        if order_pattern.search(content):
            score += 0.2
        
        return min(1.0, score)

    def _detect_mailing_list(self, headers: Dict, content: str) -> Optional[str]:
        """Detect if email is from a mailing list and extract list name."""
        # Check standard mailing list headers
        list_headers = ['List-Id', 'List-Unsubscribe', 'Mailing-List', 'X-Mailing-List']
        
        for header in list_headers:
            if header in headers:
                list_value = headers[header]
                # Extract list name from various formats
                match = re.search(r'<([^>]+)>', list_value)
                if match:
                    return match.group(1)
                return list_value.split()[0]
        
        # Check for newsletter patterns
        if re.search(r'newsletter|bulletin|digest', content, re.IGNORECASE):
            return "newsletter"
        
        return None

    def _is_critical_sender(self, sender: str) -> bool:
        """Check if sender is marked as critical."""
        return any(critical in sender for critical in self.critical_senders)

    def _has_critical_keywords(self, content: str) -> bool:
        """Check for critical keywords in email content."""
        critical_patterns = [
            r'urgent',
            r'important',
            r'security\s+alert',
            r'account\s+suspended',
            r'verify\s+account',
            r'tax\s+notice',
            r'legal\s+notice',
        ]
        
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in critical_patterns)

    def _is_automated_message(self, headers: Dict, content: str) -> bool:
        """Detect if message is automated."""
        # Check headers for automation indicators
        auto_headers = ['X-Auto-Response-Suppress', 'Auto-Submitted', 'X-Autoreply']
        if any(header in headers for header in auto_headers):
            return True
        
        # Check for automated message patterns
        auto_patterns = [
            r'do\s+not\s+reply',
            r'noreply',
            r'automated\s+message',
            r'auto.*generated',
        ]
        
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in auto_patterns)

    def _extract_merchant_name(self, email: ProcessedEmail) -> Optional[str]:
        """Extract merchant name from receipt email."""
        # Try to extract from sender name first
        if email.sender_name:
            return email.sender_name
        
        # Extract from sender email domain
        sender_parts = email.sender.split('@')
        if len(sender_parts) == 2:
            domain = sender_parts[1].split('.')[0]
            return domain.title()
        
        return None

    def _extract_unsubscribe_link(self, content: str) -> Optional[str]:
        """Extract unsubscribe link from email content."""
        if not content:
            return None
        
        # Look for unsubscribe URLs
        unsubscribe_patterns = [
            r'<a[^>]*href=["\']([^"\']*unsubscribe[^"\']*)["\'][^>]*>',
            r'https?://[^\s]*unsubscribe[^\s]*',
        ]
        
        for pattern in unsubscribe_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1) if pattern.startswith('<a') else match.group(0)
        
        return None