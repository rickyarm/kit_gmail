"""Main Gmail management functionality."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

from googleapiclient.errors import HttpError

from .gmail_auth import GmailAuth
from .email_processor import EmailProcessor
from ..services.ai_service import AIService
from ..utils.config import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)


class GmailManager:
    """Main class for managing Gmail operations."""

    def __init__(self) -> None:
        self.auth = GmailAuth()
        self.processor = EmailProcessor()
        self.ai_service = AIService()
        self._service = None

    @property
    def service(self):
        """Get Gmail API service instance."""
        if not self._service:
            self._service = self.auth.get_gmail_service()
        return self._service

    def get_messages(
        self,
        query: str = "",
        max_results: int = 100,
        label_ids: Optional[List[str]] = None,
    ) -> List[Dict]:
        """Retrieve messages from Gmail."""
        try:
            messages = []
            page_token = None
            
            while len(messages) < max_results:
                results = (
                    self.service.users()
                    .messages()
                    .list(
                        userId="me",
                        q=query,
                        labelIds=label_ids,
                        maxResults=min(100, max_results - len(messages)),
                        pageToken=page_token,
                    )
                    .execute()
                )

                batch_messages = results.get("messages", [])
                if not batch_messages:
                    break

                messages.extend(batch_messages)
                page_token = results.get("nextPageToken")
                if not page_token:
                    break

            logger.info(f"Retrieved {len(messages)} messages")
            return messages

        except HttpError as error:
            logger.error(f"Failed to retrieve messages: {error}")
            raise

    def get_message_details(self, message_id: str) -> Dict:
        """Get detailed information about a specific message."""
        try:
            message = (
                self.service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )
            return message
        except HttpError as error:
            logger.error(f"Failed to get message details for {message_id}: {error}")
            raise

    def batch_get_messages(self, message_ids: List[str]) -> List[Dict]:
        """Efficiently retrieve multiple message details."""
        messages = []
        batch_size = settings.max_email_batch_size
        
        for i in range(0, len(message_ids), batch_size):
            batch = message_ids[i : i + batch_size]
            batch_messages = []
            
            for msg_id in batch:
                try:
                    message = self.get_message_details(msg_id)
                    batch_messages.append(message)
                except HttpError as e:
                    logger.warning(f"Failed to get message {msg_id}: {e}")
                    continue
            
            messages.extend(batch_messages)
            logger.debug(f"Processed batch {i//batch_size + 1}, got {len(batch_messages)} messages")

        return messages

    def cleanup_mailbox(
        self,
        days_old: int = 30,
        delete_junk: bool = True,
        archive_old: bool = True,
    ) -> Dict[str, int]:
        """Perform comprehensive mailbox cleanup."""
        logger.info(f"Starting mailbox cleanup (days_old={days_old})")
        
        stats = {
            "processed": 0,
            "deleted": 0,
            "archived": 0,
            "organized": 0,
        }

        # Get old messages
        date_cutoff = datetime.now() - timedelta(days=days_old)
        query = f"older_than:{days_old}d"
        
        old_messages = self.get_messages(query=query, max_results=1000)
        message_details = self.batch_get_messages([m["id"] for m in old_messages])

        for message in message_details:
            stats["processed"] += 1
            
            # Process message and determine action
            processed_email = self.processor.process_email(message)
            
            if delete_junk and processed_email.is_junk:
                self.delete_message(message["id"])
                stats["deleted"] += 1
                logger.debug(f"Deleted junk message: {processed_email.subject}")
                
            elif archive_old and not processed_email.is_critical:
                self.archive_message(message["id"])
                stats["archived"] += 1
                logger.debug(f"Archived old message: {processed_email.subject}")
            
            # Organize non-deleted messages
            if not (delete_junk and processed_email.is_junk):
                self.organize_message(message, processed_email)
                stats["organized"] += 1

        logger.info(f"Mailbox cleanup completed: {stats}")
        return stats

    def organize_message(self, message: Dict, processed_email) -> None:
        """Organize a message by applying appropriate labels."""
        labels_to_add = []
        labels_to_remove = []

        # Receipt organization
        if processed_email.is_receipt:
            labels_to_add.append("Receipts")
            if processed_email.merchant:
                labels_to_add.append(f"Receipts/{processed_email.merchant}")

        # Mailing list organization
        if processed_email.is_mailing_list:
            labels_to_add.append("Mailing Lists")
            if processed_email.list_name:
                labels_to_add.append(f"Lists/{processed_email.list_name}")

        # Critical email organization
        if processed_email.is_critical:
            labels_to_add.append("Important")

        # Apply labels
        if labels_to_add or labels_to_remove:
            self.modify_message_labels(
                message["id"], labels_to_add, labels_to_remove
            )

    def modify_message_labels(
        self,
        message_id: str,
        add_labels: List[str] = None,
        remove_labels: List[str] = None,
    ) -> None:
        """Add or remove labels from a message."""
        if not add_labels and not remove_labels:
            return

        # Get or create label IDs
        add_label_ids = []
        if add_labels:
            for label_name in add_labels:
                label_id = self.get_or_create_label(label_name)
                add_label_ids.append(label_id)

        remove_label_ids = []
        if remove_labels:
            for label_name in remove_labels:
                label_id = self.get_label_id(label_name)
                if label_id:
                    remove_label_ids.append(label_id)

        try:
            self.service.users().messages().modify(
                userId="me",
                id=message_id,
                body={
                    "addLabelIds": add_label_ids,
                    "removeLabelIds": remove_label_ids,
                },
            ).execute()
            logger.debug(f"Modified labels for message {message_id}")
        except HttpError as error:
            logger.error(f"Failed to modify labels for {message_id}: {error}")

    def get_or_create_label(self, label_name: str) -> str:
        """Get existing label ID or create new label."""
        try:
            # Try to get existing label
            labels = self.service.users().labels().list(userId="me").execute()
            for label in labels.get("labels", []):
                if label["name"] == label_name:
                    return label["id"]

            # Create new label
            label_object = {
                "name": label_name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            }
            
            created_label = (
                self.service.users()
                .labels()
                .create(userId="me", body=label_object)
                .execute()
            )
            
            logger.info(f"Created new label: {label_name}")
            return created_label["id"]

        except HttpError as error:
            logger.error(f"Failed to get or create label {label_name}: {error}")
            raise

    def get_label_id(self, label_name: str) -> Optional[str]:
        """Get label ID by name."""
        try:
            labels = self.service.users().labels().list(userId="me").execute()
            for label in labels.get("labels", []):
                if label["name"] == label_name:
                    return label["id"]
            return None
        except HttpError as error:
            logger.error(f"Failed to get label ID for {label_name}: {error}")
            return None

    def delete_message(self, message_id: str) -> None:
        """Permanently delete a message."""
        try:
            self.service.users().messages().delete(userId="me", id=message_id).execute()
            logger.debug(f"Deleted message {message_id}")
        except HttpError as error:
            logger.error(f"Failed to delete message {message_id}: {error}")

    def archive_message(self, message_id: str) -> None:
        """Archive a message (remove from inbox)."""
        try:
            self.service.users().messages().modify(
                userId="me",
                id=message_id,
                body={"removeLabelIds": ["INBOX"]},
            ).execute()
            logger.debug(f"Archived message {message_id}")
        except HttpError as error:
            logger.error(f"Failed to archive message {message_id}: {error}")

    async def generate_email_summary(
        self, days: int = 7, summary_type: str = "daily"
    ) -> str:
        """Generate AI-powered email summary."""
        logger.info(f"Generating {summary_type} email summary for {days} days")
        
        # Get recent messages
        query = f"newer_than:{days}d"
        messages = self.get_messages(query=query, max_results=200)
        message_details = self.batch_get_messages([m["id"] for m in messages])

        # Process emails for summary
        processed_emails = []
        for message in message_details:
            processed_email = self.processor.process_email(message)
            processed_emails.append(processed_email)

        # Generate AI summary
        summary = await self.ai_service.generate_email_summary(
            processed_emails, days, summary_type
        )
        
        logger.info("Email summary generated successfully")
        return summary

    def get_mailbox_stats(self) -> Dict[str, int]:
        """Get comprehensive mailbox statistics."""
        stats = {}
        
        try:
            # Get label statistics
            labels = self.service.users().labels().list(userId="me").execute()
            
            for label in labels.get("labels", []):
                label_name = label["name"]
                label_data = (
                    self.service.users()
                    .labels()
                    .get(userId="me", id=label["id"])
                    .execute()
                )
                stats[label_name] = {
                    "messages_total": label_data.get("messagesTotal", 0),
                    "messages_unread": label_data.get("messagesUnread", 0),
                    "threads_total": label_data.get("threadsTotal", 0),
                    "threads_unread": label_data.get("threadsUnread", 0),
                }

        except HttpError as error:
            logger.error(f"Failed to get mailbox stats: {error}")
            
        return stats