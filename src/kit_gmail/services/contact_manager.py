"""Contact management and email address analysis."""

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
import sqlite3
from pathlib import Path

from ..core.email_processor import ProcessedEmail
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Contact:
    """Represents a contact extracted from email communications."""
    
    email: str
    name: Optional[str] = None
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    email_count: int = 0
    sent_count: int = 0
    received_count: int = 0
    
    # Classification
    is_frequent: bool = False
    is_important: bool = False
    is_spam: bool = False
    is_automated: bool = False
    
    # Associated data
    domains: Set[str] = field(default_factory=set)
    subjects_seen: List[str] = field(default_factory=list)
    labels_associated: Set[str] = field(default_factory=set)
    
    # Metadata
    confidence_score: float = 0.0
    notes: List[str] = field(default_factory=list)


class ContactManager:
    """Manages contacts and email address analysis."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path or str(Path.home() / ".kit_gmail" / "contacts.db")
        self.contacts: Dict[str, Contact] = {}
        self._ensure_db_setup()

    def _ensure_db_setup(self) -> None:
        """Ensure database is set up with required tables."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS contacts (
                    email TEXT PRIMARY KEY,
                    name TEXT,
                    first_seen TIMESTAMP,
                    last_seen TIMESTAMP,
                    email_count INTEGER DEFAULT 0,
                    sent_count INTEGER DEFAULT 0,
                    received_count INTEGER DEFAULT 0,
                    is_frequent BOOLEAN DEFAULT 0,
                    is_important BOOLEAN DEFAULT 0,
                    is_spam BOOLEAN DEFAULT 0,
                    is_automated BOOLEAN DEFAULT 0,
                    confidence_score REAL DEFAULT 0.0,
                    notes TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS contact_domains (
                    contact_email TEXT,
                    domain TEXT,
                    FOREIGN KEY (contact_email) REFERENCES contacts (email)
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS contact_subjects (
                    contact_email TEXT,
                    subject TEXT,
                    seen_count INTEGER DEFAULT 1,
                    FOREIGN KEY (contact_email) REFERENCES contacts (email)
                )
            ''')

    def analyze_emails(self, emails: List[ProcessedEmail]) -> Dict[str, any]:
        """Analyze a batch of emails to extract and update contact information."""
        stats = {
            "emails_processed": 0,
            "new_contacts": 0,
            "updated_contacts": 0,
            "frequent_contacts": 0,
            "spam_contacts": 0,
        }
        
        for email in emails:
            stats["emails_processed"] += 1
            
            # Process sender
            sender_updated = self._update_contact_from_email(email, is_sender=True)
            if sender_updated == "new":
                stats["new_contacts"] += 1
            elif sender_updated == "updated":
                stats["updated_contacts"] += 1
                
            # Process recipients
            for recipient in email.recipients:
                recipient_updated = self._update_contact_from_email(email, is_sender=False, contact_email=recipient)
                if recipient_updated == "new":
                    stats["new_contacts"] += 1
                elif recipient_updated == "updated":
                    stats["updated_contacts"] += 1

        # Classify contacts after processing all emails
        self._classify_contacts()
        
        # Count classifications
        for contact in self.contacts.values():
            if contact.is_frequent:
                stats["frequent_contacts"] += 1
            if contact.is_spam:
                stats["spam_contacts"] += 1

        # Save to database
        self._save_contacts_to_db()
        
        logger.info(f"Contact analysis completed: {stats}")
        return stats

    def _update_contact_from_email(
        self, 
        email: ProcessedEmail, 
        is_sender: bool, 
        contact_email: Optional[str] = None
    ) -> str:
        """Update contact information from an email."""
        email_addr = contact_email or email.sender
        
        # Get or create contact
        if email_addr not in self.contacts:
            contact = Contact(
                email=email_addr,
                first_seen=email.date,
                last_seen=email.date,
            )
            self.contacts[email_addr] = contact
            result = "new"
        else:
            contact = self.contacts[email_addr]
            result = "updated"

        # Update contact information
        contact.last_seen = max(contact.last_seen or email.date, email.date)
        contact.first_seen = min(contact.first_seen or email.date, email.date)
        
        # Update name if available and not set
        if not contact.name and is_sender and email.sender_name:
            contact.name = email.sender_name

        # Update counts
        contact.email_count += 1
        if is_sender:
            contact.received_count += 1
        else:
            contact.sent_count += 1

        # Add domain
        domain = email_addr.split('@')[-1].lower()
        contact.domains.add(domain)

        # Track subjects (limit to prevent memory issues)
        if len(contact.subjects_seen) < 50:
            contact.subjects_seen.append(email.subject[:100])

        # Add labels
        contact.labels_associated.update(email.labels)

        # Update classification flags based on email
        if email.is_junk:
            contact.is_spam = True
        if email.is_automated:
            contact.is_automated = True

        return result

    def _classify_contacts(self) -> None:
        """Classify contacts based on interaction patterns."""
        if not self.contacts:
            return

        # Calculate thresholds
        email_counts = [c.email_count for c in self.contacts.values()]
        avg_count = sum(email_counts) / len(email_counts)
        frequent_threshold = max(10, avg_count * 1.5)

        for contact in self.contacts.values():
            confidence_factors = []
            
            # Mark frequent contacts
            if contact.email_count >= frequent_threshold:
                contact.is_frequent = True
                confidence_factors.append(f"frequent_emails: {contact.email_count}")

            # Mark important contacts (heuristics)
            important_score = self._calculate_importance_score(contact)
            if important_score > 0.6:
                contact.is_important = True
                confidence_factors.append(f"importance_score: {important_score:.2f}")

            # Refine spam detection
            spam_score = self._calculate_spam_score(contact)
            if spam_score > 0.7:
                contact.is_spam = True
                confidence_factors.append(f"spam_score: {spam_score:.2f}")

            # Calculate confidence score
            contact.confidence_score = min(1.0, len(confidence_factors) * 0.3)
            contact.notes = confidence_factors

    def _calculate_importance_score(self, contact: Contact) -> float:
        """Calculate importance score for a contact."""
        score = 0.0
        
        # High email frequency
        if contact.email_count > 20:
            score += 0.3
        
        # Bidirectional communication
        if contact.sent_count > 0 and contact.received_count > 0:
            score += 0.4
        
        # Professional domains
        professional_domains = {
            'gov', 'edu', 'org', 'bank', 'insurance', 'legal', 'medical'
        }
        if any(domain_part in ' '.join(contact.domains) 
               for domain_part in professional_domains):
            score += 0.3
        
        # Long-term correspondence
        if contact.first_seen and contact.last_seen:
            days_span = (contact.last_seen - contact.first_seen).days
            if days_span > 365:  # Over a year
                score += 0.2

        # Not automated
        if not contact.is_automated:
            score += 0.1

        return min(1.0, score)

    def _calculate_spam_score(self, contact: Contact) -> float:
        """Calculate spam probability for a contact."""
        score = 0.0
        
        # High volume, one-way communication
        if contact.email_count > 10 and contact.sent_count == 0:
            score += 0.4
        
        # Spam-like domains
        spam_domains = {'noreply', 'marketing', 'promo', 'newsletter', 'deals'}
        if any(spam_term in ' '.join(contact.domains) 
               for spam_term in spam_domains):
            score += 0.3
        
        # No personal name
        if not contact.name or contact.name.lower() in ['noreply', 'no-reply']:
            score += 0.2
        
        # Automated messages
        if contact.is_automated:
            score += 0.3
        
        # Promotional labels
        promo_labels = {'PROMOTIONS', 'SPAM', 'JUNK'}
        if any(label in contact.labels_associated for label in promo_labels):
            score += 0.4

        return min(1.0, score)

    def get_contact_stats(self) -> Dict[str, any]:
        """Get comprehensive contact statistics."""
        if not self.contacts:
            return {"total_contacts": 0}

        total = len(self.contacts)
        frequent = sum(1 for c in self.contacts.values() if c.is_frequent)
        important = sum(1 for c in self.contacts.values() if c.is_important)
        spam = sum(1 for c in self.contacts.values() if c.is_spam)
        automated = sum(1 for c in self.contacts.values() if c.is_automated)
        
        # Domain analysis
        domain_counter = Counter()
        for contact in self.contacts.values():
            domain_counter.update(contact.domains)
        
        # Communication patterns
        total_emails = sum(c.email_count for c in self.contacts.values())
        avg_emails = total_emails / total if total > 0 else 0
        
        return {
            "total_contacts": total,
            "frequent_contacts": frequent,
            "important_contacts": important,
            "spam_contacts": spam,
            "automated_contacts": automated,
            "total_emails": total_emails,
            "avg_emails_per_contact": round(avg_emails, 2),
            "top_domains": dict(domain_counter.most_common(10)),
            "classification_coverage": {
                "frequent": f"{frequent/total*100:.1f}%" if total > 0 else "0%",
                "important": f"{important/total*100:.1f}%" if total > 0 else "0%",
                "spam": f"{spam/total*100:.1f}%" if total > 0 else "0%",
            }
        }

    def get_frequent_contacts(self, limit: int = 50) -> List[Contact]:
        """Get most frequent contacts."""
        frequent = [c for c in self.contacts.values() if c.is_frequent]
        return sorted(frequent, key=lambda x: x.email_count, reverse=True)[:limit]

    def get_spam_contacts(self) -> List[Contact]:
        """Get contacts identified as spam."""
        return [c for c in self.contacts.values() if c.is_spam]

    def get_important_contacts(self) -> List[Contact]:
        """Get contacts marked as important."""
        return [c for c in self.contacts.values() if c.is_important]

    def find_contacts(self, query: str) -> List[Contact]:
        """Search contacts by email or name."""
        query = query.lower()
        matches = []
        
        for contact in self.contacts.values():
            if (query in contact.email.lower() or 
                (contact.name and query in contact.name.lower())):
                matches.append(contact)
        
        return sorted(matches, key=lambda x: x.email_count, reverse=True)

    def get_contact_suggestions(self) -> Dict[str, List[str]]:
        """Get suggestions for contact management actions."""
        suggestions = {
            "contacts_to_block": [],
            "contacts_to_whitelist": [],
            "potential_duplicates": [],
            "inactive_contacts": [],
        }

        # Contacts to potentially block (high spam score)
        for contact in self.contacts.values():
            spam_score = self._calculate_spam_score(contact)
            if spam_score > 0.8:
                suggestions["contacts_to_block"].append(contact.email)

        # Contacts to whitelist (important but not marked)
        for contact in self.contacts.values():
            if (not contact.is_important and 
                self._calculate_importance_score(contact) > 0.7):
                suggestions["contacts_to_whitelist"].append(contact.email)

        # Find potential duplicates (same name, different emails)
        name_to_emails = defaultdict(list)
        for contact in self.contacts.values():
            if contact.name:
                name_to_emails[contact.name.lower()].append(contact.email)
        
        for name, emails in name_to_emails.items():
            if len(emails) > 1:
                suggestions["potential_duplicates"].extend(emails)

        # Inactive contacts (no recent activity)
        cutoff_date = datetime.now() - timedelta(days=365)
        for contact in self.contacts.values():
            if (contact.last_seen and 
                contact.last_seen < cutoff_date and 
                not contact.is_important):
                suggestions["inactive_contacts"].append(contact.email)

        return suggestions

    def _save_contacts_to_db(self) -> None:
        """Save contacts to SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            # Clear existing data
            conn.execute("DELETE FROM contact_subjects")
            conn.execute("DELETE FROM contact_domains")
            conn.execute("DELETE FROM contacts")
            
            # Insert contacts
            for contact in self.contacts.values():
                conn.execute('''
                    INSERT OR REPLACE INTO contacts 
                    (email, name, first_seen, last_seen, email_count, sent_count, 
                     received_count, is_frequent, is_important, is_spam, is_automated, 
                     confidence_score, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    contact.email, contact.name, contact.first_seen, contact.last_seen,
                    contact.email_count, contact.sent_count, contact.received_count,
                    contact.is_frequent, contact.is_important, contact.is_spam,
                    contact.is_automated, contact.confidence_score,
                    '; '.join(contact.notes)
                ))
                
                # Insert domains
                for domain in contact.domains:
                    conn.execute(
                        "INSERT INTO contact_domains (contact_email, domain) VALUES (?, ?)",
                        (contact.email, domain)
                    )
                
                # Insert subjects (limit to recent ones)
                subject_counter = Counter(contact.subjects_seen)
                for subject, count in subject_counter.most_common(20):
                    conn.execute(
                        "INSERT INTO contact_subjects (contact_email, subject, seen_count) VALUES (?, ?, ?)",
                        (contact.email, subject, count)
                    )

    def load_contacts_from_db(self) -> None:
        """Load contacts from SQLite database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Load contacts
                contacts_cursor = conn.execute('''
                    SELECT * FROM contacts
                ''')
                
                for row in contacts_cursor:
                    contact = Contact(
                        email=row['email'],
                        name=row['name'],
                        first_seen=datetime.fromisoformat(row['first_seen']) if row['first_seen'] else None,
                        last_seen=datetime.fromisoformat(row['last_seen']) if row['last_seen'] else None,
                        email_count=row['email_count'],
                        sent_count=row['sent_count'],
                        received_count=row['received_count'],
                        is_frequent=bool(row['is_frequent']),
                        is_important=bool(row['is_important']),
                        is_spam=bool(row['is_spam']),
                        is_automated=bool(row['is_automated']),
                        confidence_score=row['confidence_score'],
                        notes=row['notes'].split('; ') if row['notes'] else [],
                    )
                    
                    # Load domains
                    domains_cursor = conn.execute(
                        "SELECT domain FROM contact_domains WHERE contact_email = ?",
                        (contact.email,)
                    )
                    contact.domains = {row[0] for row in domains_cursor}
                    
                    # Load subjects
                    subjects_cursor = conn.execute(
                        "SELECT subject FROM contact_subjects WHERE contact_email = ?",
                        (contact.email,)
                    )
                    contact.subjects_seen = [row[0] for row in subjects_cursor]
                    
                    self.contacts[contact.email] = contact

                logger.info(f"Loaded {len(self.contacts)} contacts from database")
                
        except sqlite3.Error as e:
            logger.error(f"Failed to load contacts from database: {e}")
            self.contacts = {}