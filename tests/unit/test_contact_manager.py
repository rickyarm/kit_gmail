"""Unit tests for ContactManager."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, Mock
import sqlite3

from kit_gmail.services.contact_manager import ContactManager, Contact


class TestContactManager:
    
    @pytest.fixture
    def contact_manager(self, temp_db_path):
        """ContactManager instance with temporary database."""
        return ContactManager(db_path=temp_db_path)
    
    def test_init(self, contact_manager, temp_db_path):
        """Test ContactManager initialization."""
        assert contact_manager.db_path == temp_db_path
        assert contact_manager.contacts == {}
        
        # Check database tables were created
        with sqlite3.connect(temp_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
        assert "contacts" in tables
        assert "contact_domains" in tables
        assert "contact_subjects" in tables
    
    def test_update_contact_from_email_new(self, contact_manager, sample_processed_email):
        """Test updating contact from email (new contact)."""
        result = contact_manager._update_contact_from_email(
            sample_processed_email, is_sender=True
        )
        
        assert result == "new"
        assert sample_processed_email.sender in contact_manager.contacts
        
        contact = contact_manager.contacts[sample_processed_email.sender]
        assert contact.email == sample_processed_email.sender
        assert contact.name == sample_processed_email.sender_name
        assert contact.email_count == 1
        assert contact.received_count == 1
        assert contact.sent_count == 0
        
    def test_update_contact_from_email_existing(self, contact_manager, sample_processed_email):
        """Test updating existing contact from email."""
        # Add contact first
        contact_manager._update_contact_from_email(
            sample_processed_email, is_sender=True
        )
        
        # Update again
        result = contact_manager._update_contact_from_email(
            sample_processed_email, is_sender=False, contact_email=sample_processed_email.sender
        )
        
        assert result == "updated"
        
        contact = contact_manager.contacts[sample_processed_email.sender]
        assert contact.email_count == 2
        assert contact.received_count == 1
        assert contact.sent_count == 1
        
    def test_analyze_emails(self, contact_manager, sample_processed_email):
        """Test email analysis for contact extraction."""
        emails = [sample_processed_email] * 5  # 5 emails from same sender
        
        stats = contact_manager.analyze_emails(emails)
        
        assert stats["emails_processed"] == 5
        assert stats["new_contacts"] >= 1
        assert len(contact_manager.contacts) >= 1
        
    def test_classify_contacts(self, contact_manager):
        """Test contact classification."""
        # Add high-frequency contact
        frequent_contact = Contact(
            email="frequent@example.com",
            email_count=50,
            sent_count=10,
            received_count=40
        )
        contact_manager.contacts[frequent_contact.email] = frequent_contact
        
        # Add low-frequency contact
        regular_contact = Contact(
            email="regular@example.com", 
            email_count=5,
            sent_count=1,
            received_count=4
        )
        contact_manager.contacts[regular_contact.email] = regular_contact
        
        contact_manager._classify_contacts()
        
        assert frequent_contact.is_frequent
        assert not regular_contact.is_frequent
        
    def test_calculate_importance_score(self, contact_manager):
        """Test importance score calculation."""
        # Important contact (high volume, bidirectional, professional domain)
        important_contact = Contact(
            email="admin@bank.com",
            email_count=30,
            sent_count=5,
            received_count=25,
            first_seen=datetime.now() - timedelta(days=400),
            last_seen=datetime.now() - timedelta(days=1),
            is_automated=False
        )
        important_contact.domains.add("bank.com")
        
        score = contact_manager._calculate_importance_score(important_contact)
        assert score > 0.6
        
        # Unimportant contact
        unimportant_contact = Contact(
            email="marketing@shop.com",
            email_count=2,
            sent_count=0,
            received_count=2,
            is_automated=True
        )
        
        score = contact_manager._calculate_importance_score(unimportant_contact)
        assert score < 0.4
        
    def test_calculate_spam_score(self, contact_manager):
        """Test spam score calculation."""
        # Spam-like contact
        spam_contact = Contact(
            email="noreply@marketing.com",
            email_count=20,
            sent_count=0,
            received_count=20,
            is_automated=True
        )
        spam_contact.domains.add("marketing.com")
        spam_contact.labels_associated.add("PROMOTIONS")
        
        score = contact_manager._calculate_spam_score(spam_contact)
        assert score > 0.7
        
        # Regular contact
        regular_contact = Contact(
            email="friend@gmail.com",
            name="Friend Name",
            email_count=10,
            sent_count=5,
            received_count=5,
            is_automated=False
        )
        
        score = contact_manager._calculate_spam_score(regular_contact)
        assert score < 0.3
        
    def test_get_contact_stats(self, contact_manager):
        """Test contact statistics generation."""
        # Add some test contacts
        contacts = [
            Contact(email="freq@example.com", email_count=50, is_frequent=True),
            Contact(email="imp@bank.com", email_count=10, is_important=True),
            Contact(email="spam@marketing.com", email_count=5, is_spam=True),
            Contact(email="auto@system.com", email_count=15, is_automated=True)
        ]
        
        for contact in contacts:
            contact_manager.contacts[contact.email] = contact
        
        stats = contact_manager.get_contact_stats()
        
        assert stats["total_contacts"] == 4
        assert stats["frequent_contacts"] == 1
        assert stats["important_contacts"] == 1
        assert stats["spam_contacts"] == 1
        assert stats["automated_contacts"] == 1
        assert stats["total_emails"] == 80  # Sum of email counts
        assert stats["avg_emails_per_contact"] == 20.0
        
    def test_get_frequent_contacts(self, contact_manager):
        """Test getting frequent contacts."""
        # Add contacts with different email counts
        contacts = [
            Contact(email="high@example.com", email_count=100, is_frequent=True),
            Contact(email="medium@example.com", email_count=50, is_frequent=True),
            Contact(email="low@example.com", email_count=5, is_frequent=False)
        ]
        
        for contact in contacts:
            contact_manager.contacts[contact.email] = contact
        
        frequent = contact_manager.get_frequent_contacts(limit=10)
        
        # Should return only frequent contacts, sorted by email count
        assert len(frequent) == 2
        assert frequent[0].email_count >= frequent[1].email_count
        assert all(c.is_frequent for c in frequent)
        
    def test_find_contacts(self, contact_manager):
        """Test contact search."""
        # Add test contacts
        contacts = [
            Contact(email="john.doe@example.com", name="John Doe", email_count=10),
            Contact(email="jane.smith@company.com", name="Jane Smith", email_count=8),
            Contact(email="support@service.com", name="Support Team", email_count=15)
        ]
        
        for contact in contacts:
            contact_manager.contacts[contact.email] = contact
        
        # Search by email
        results = contact_manager.find_contacts("john")
        assert len(results) == 1
        assert results[0].email == "john.doe@example.com"
        
        # Search by name
        results = contact_manager.find_contacts("jane")
        assert len(results) == 1
        assert results[0].name == "Jane Smith"
        
        # Search by partial match
        results = contact_manager.find_contacts("example")
        assert len(results) == 1
        
    def test_get_contact_suggestions(self, contact_manager):
        """Test contact management suggestions."""
        # Add various types of contacts
        contacts = [
            Contact(email="spam@marketing.com", is_spam=True, email_count=50),
            Contact(email="important@bank.com", email_count=20, is_important=False),  # Should be important
            Contact(email="old@inactive.com", email_count=5, 
                   last_seen=datetime.now() - timedelta(days=400)),
            Contact(email="duplicate1@same.com", name="Same Person", email_count=10),
            Contact(email="duplicate2@same.com", name="Same Person", email_count=8)
        ]
        
        for contact in contacts:
            contact_manager.contacts[contact.email] = contact
        
        suggestions = contact_manager.get_contact_suggestions()
        
        # Should suggest blocking spam
        assert len(suggestions["contacts_to_block"]) >= 1
        
        # Should suggest potential duplicates
        assert len(suggestions["potential_duplicates"]) >= 2
        
        # Should suggest inactive contacts
        assert len(suggestions["inactive_contacts"]) >= 1
        
    def test_save_and_load_contacts(self, contact_manager):
        """Test saving and loading contacts from database."""
        # Add test contact
        contact = Contact(
            email="test@example.com",
            name="Test User",
            first_seen=datetime.now() - timedelta(days=30),
            last_seen=datetime.now() - timedelta(days=1),
            email_count=15,
            sent_count=5,
            received_count=10,
            is_frequent=True,
            is_important=False,
            confidence_score=0.8
        )
        contact.domains.add("example.com")
        contact.subjects_seen = ["Test Subject 1", "Test Subject 2"]
        contact.notes = ["High engagement", "Regular correspondent"]
        
        contact_manager.contacts[contact.email] = contact
        
        # Save to database
        contact_manager._save_contacts_to_db()
        
        # Clear contacts and reload
        contact_manager.contacts.clear()
        contact_manager.load_contacts_from_db()
        
        # Verify loaded contact
        assert len(contact_manager.contacts) == 1
        loaded_contact = contact_manager.contacts["test@example.com"]
        
        assert loaded_contact.email == contact.email
        assert loaded_contact.name == contact.name
        assert loaded_contact.email_count == contact.email_count
        assert loaded_contact.is_frequent == contact.is_frequent
        assert "example.com" in loaded_contact.domains
        assert len(loaded_contact.subjects_seen) == 2