"""AI service integration for email summarization and analysis."""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Union
import json

import anthropic
import openai
import httpx

from ..core.email_processor import ProcessedEmail
from ..utils.config import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)


class AIProvider(ABC):
    """Abstract base class for AI service providers."""
    
    @abstractmethod
    async def generate_summary(self, prompt: str, context: str) -> str:
        """Generate a summary using the AI provider."""
        pass
    
    @abstractmethod
    async def analyze_email(self, email: ProcessedEmail) -> Dict[str, any]:
        """Analyze a single email for insights."""
        pass


class AnthropicProvider(AIProvider):
    """Anthropic Claude AI provider."""
    
    def __init__(self, api_key: str) -> None:
        self.client = anthropic.Anthropic(api_key=api_key)
    
    async def generate_summary(self, prompt: str, context: str) -> str:
        """Generate summary using Claude."""
        try:
            message = await asyncio.to_thread(
                self.client.messages.create,
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                messages=[
                    {
                        "role": "user",
                        "content": f"{prompt}\n\nContext:\n{context}"
                    }
                ]
            )
            return message.content[0].text
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise
    
    async def analyze_email(self, email: ProcessedEmail) -> Dict[str, any]:
        """Analyze email using Claude."""
        prompt = f"""
        Analyze this email and provide insights:
        
        Subject: {email.subject}
        From: {email.sender} ({email.sender_name or 'Unknown'})
        Date: {email.date}
        Content: {email.body_text[:1000]}...
        
        Please analyze and return:
        1. Sentiment (positive/negative/neutral)
        2. Category (personal/business/promotional/automated)
        3. Priority level (high/medium/low)
        4. Key topics/entities mentioned
        5. Recommended action
        
        Return as JSON format.
        """
        
        try:
            message = await asyncio.to_thread(
                self.client.messages.create,
                model="claude-3-5-haiku-20241022",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = message.content[0].text
            # Try to extract JSON from response
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                return {"analysis": response_text, "error": "Failed to parse JSON"}
                
        except Exception as e:
            logger.error(f"Email analysis error: {e}")
            return {"error": str(e)}


class OpenAIProvider(AIProvider):
    """OpenAI GPT provider."""
    
    def __init__(self, api_key: str) -> None:
        self.client = openai.AsyncOpenAI(api_key=api_key)
    
    async def generate_summary(self, prompt: str, context: str) -> str:
        """Generate summary using GPT."""
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert email analyst. Provide clear, concise summaries."
                    },
                    {
                        "role": "user",
                        "content": f"{prompt}\n\nContext:\n{context}"
                    }
                ],
                max_tokens=1000,
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    async def analyze_email(self, email: ProcessedEmail) -> Dict[str, any]:
        """Analyze email using GPT."""
        prompt = f"""
        Analyze this email and return insights as JSON:
        
        Subject: {email.subject}
        From: {email.sender} ({email.sender_name or 'Unknown'})
        Date: {email.date}
        Content: {email.body_text[:1000]}...
        
        Return JSON with:
        - sentiment: positive/negative/neutral
        - category: personal/business/promotional/automated
        - priority: high/medium/low
        - topics: array of key topics
        - action: recommended action
        """
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an email analyst. Always return valid JSON."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.1
            )
            
            response_text = response.choices[0].message.content
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                return {"analysis": response_text, "error": "Failed to parse JSON"}
                
        except Exception as e:
            logger.error(f"Email analysis error: {e}")
            return {"error": str(e)}


class XAIProvider(AIProvider):
    """xAI Grok provider."""
    
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.base_url = "https://api.x.ai/v1"
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {api_key}"}
        )
    
    async def generate_summary(self, prompt: str, context: str) -> str:
        """Generate summary using Grok."""
        try:
            response = await self.client.post(
                "/chat/completions",
                json={
                    "model": "grok-beta",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert email analyst. Provide clear, concise summaries."
                        },
                        {
                            "role": "user",
                            "content": f"{prompt}\n\nContext:\n{context}"
                        }
                    ],
                    "max_tokens": 1000,
                    "temperature": 0.3
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"xAI API error: {e}")
            raise
    
    async def analyze_email(self, email: ProcessedEmail) -> Dict[str, any]:
        """Analyze email using Grok."""
        prompt = f"""
        Analyze this email and return insights as JSON:
        
        Subject: {email.subject}
        From: {email.sender} ({email.sender_name or 'Unknown'})
        Date: {email.date}
        Content: {email.body_text[:1000]}...
        
        Return JSON with:
        - sentiment: positive/negative/neutral
        - category: personal/business/promotional/automated
        - priority: high/medium/low
        - topics: array of key topics
        - action: recommended action
        """
        
        try:
            response = await self.client.post(
                "/chat/completions",
                json={
                    "model": "grok-beta",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an email analyst. Always return valid JSON."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 500,
                    "temperature": 0.1
                }
            )
            response.raise_for_status()
            data = response.json()
            response_text = data["choices"][0]["message"]["content"]
            
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                return {"analysis": response_text, "error": "Failed to parse JSON"}
                
        except Exception as e:
            logger.error(f"Email analysis error: {e}")
            return {"error": str(e)}
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()


class AIService:
    """Main AI service coordinator."""
    
    def __init__(self) -> None:
        self.providers: Dict[str, AIProvider] = {}
        self._initialize_providers()
    
    def _initialize_providers(self) -> None:
        """Initialize available AI providers based on configuration."""
        if settings.anthropic_api_key:
            try:
                self.providers["anthropic"] = AnthropicProvider(settings.anthropic_api_key)
                logger.info("Initialized Anthropic provider")
            except Exception as e:
                logger.warning(f"Failed to initialize Anthropic provider: {e}")
        
        if settings.openai_api_key:
            try:
                self.providers["openai"] = OpenAIProvider(settings.openai_api_key)
                logger.info("Initialized OpenAI provider")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI provider: {e}")
        
        if settings.xai_api_key:
            try:
                self.providers["xai"] = XAIProvider(settings.xai_api_key)
                logger.info("Initialized xAI provider")
            except Exception as e:
                logger.warning(f"Failed to initialize xAI provider: {e}")
        
        if not self.providers:
            logger.warning("No AI providers initialized. AI features will not be available.")
    
    def get_provider(self, provider_name: Optional[str] = None) -> AIProvider:
        """Get AI provider instance."""
        provider_name = provider_name or settings.default_ai_service
        
        if provider_name not in self.providers:
            available = list(self.providers.keys())
            if available:
                provider_name = available[0]
                logger.info(f"Requested provider '{provider_name}' not available, using '{provider_name}'")
            else:
                raise RuntimeError("No AI providers available")
        
        return self.providers[provider_name]
    
    async def generate_email_summary(
        self,
        emails: List[ProcessedEmail],
        days: int,
        summary_type: str = "daily",
        provider_name: Optional[str] = None
    ) -> str:
        """Generate comprehensive email summary."""
        if not emails:
            return "No emails found for the specified period."
        
        provider = self.get_provider(provider_name)
        
        # Prepare email context
        context = self._prepare_email_context(emails, days)
        
        # Generate summary prompt based on type
        prompt = self._create_summary_prompt(summary_type, days, len(emails))
        
        try:
            summary = await provider.generate_summary(prompt, context)
            logger.info(f"Generated {summary_type} email summary using {provider.__class__.__name__}")
            return summary
        except Exception as e:
            logger.error(f"Failed to generate email summary: {e}")
            return f"Failed to generate summary: {str(e)}"
    
    def _prepare_email_context(self, emails: List[ProcessedEmail], days: int) -> str:
        """Prepare email context for AI analysis."""
        # Categorize emails
        categories = {
            "critical": [],
            "receipts": [],
            "junk": [],
            "mailing_lists": [],
            "personal": [],
            "business": []
        }
        
        for email in emails:
            email_summary = {
                "subject": email.subject,
                "sender": f"{email.sender_name or 'Unknown'} <{email.sender}>",
                "date": email.date.strftime("%Y-%m-%d"),
                "snippet": email.body_text[:200] + "..." if len(email.body_text) > 200 else email.body_text
            }
            
            if email.is_critical:
                categories["critical"].append(email_summary)
            elif email.is_receipt:
                categories["receipts"].append(email_summary)
            elif email.is_junk:
                categories["junk"].append(email_summary)
            elif email.is_mailing_list:
                categories["mailing_lists"].append(email_summary)
            elif email.sender_name:
                categories["personal"].append(email_summary)
            else:
                categories["business"].append(email_summary)
        
        # Build context string
        context_parts = [f"Email Summary for {days} days ({len(emails)} total emails):\n"]
        
        for category, email_list in categories.items():
            if email_list:
                context_parts.append(f"\n{category.upper()} EMAILS ({len(email_list)}):")
                for i, email in enumerate(email_list[:10], 1):  # Limit to avoid token limits
                    context_parts.append(
                        f"{i}. {email['subject']} - {email['sender']} ({email['date']})"
                    )
                    if email['snippet']:
                        context_parts.append(f"   Preview: {email['snippet']}")
                
                if len(email_list) > 10:
                    context_parts.append(f"   ... and {len(email_list) - 10} more emails")
        
        return "\n".join(context_parts)
    
    def _create_summary_prompt(self, summary_type: str, days: int, email_count: int) -> str:
        """Create appropriate summary prompt."""
        base_prompt = f"""
        Please analyze and summarize the following {email_count} emails from the past {days} days.
        
        Provide a comprehensive {summary_type} summary that includes:
        1. **Overview**: Total emails and key statistics
        2. **Important/Critical Items**: Urgent emails that need attention
        3. **Receipts & Financial**: Purchase confirmations, invoices, financial updates
        4. **Communication Highlights**: Key personal or business correspondence
        5. **Mailing Lists & Newsletters**: Subscriptions and automated updates
        6. **Action Items**: Emails requiring follow-up or response
        7. **Cleanup Opportunities**: Junk emails and unsubscribe suggestions
        
        Format the summary clearly with headers and bullet points for easy reading.
        Focus on actionable insights and prioritize important information.
        """
        
        if summary_type == "weekly":
            base_prompt += "\nProvide a week-over-week comparison if applicable and highlight trends."
        elif summary_type == "monthly":
            base_prompt += "\nInclude monthly patterns and suggest organizational improvements."
        
        return base_prompt
    
    async def analyze_batch_emails(
        self,
        emails: List[ProcessedEmail],
        provider_name: Optional[str] = None
    ) -> List[Dict[str, any]]:
        """Analyze a batch of emails for insights."""
        provider = self.get_provider(provider_name)
        
        # Limit batch size to avoid API limits
        batch_size = 10
        results = []
        
        for i in range(0, len(emails), batch_size):
            batch = emails[i:i + batch_size]
            batch_results = await asyncio.gather(
                *[provider.analyze_email(email) for email in batch],
                return_exceptions=True
            )
            
            for email, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.warning(f"Failed to analyze email {email.message_id}: {result}")
                    results.append({"error": str(result), "email_id": email.message_id})
                else:
                    result["email_id"] = email.message_id
                    results.append(result)
        
        return results
    
    async def get_email_insights(
        self,
        emails: List[ProcessedEmail],
        insight_type: str = "patterns",
        provider_name: Optional[str] = None
    ) -> Dict[str, any]:
        """Generate specific insights about email patterns."""
        provider = self.get_provider(provider_name)
        
        if insight_type == "patterns":
            prompt = """
            Analyze the email patterns and provide insights about:
            1. Most active senders and their communication patterns
            2. Email volume trends by day/time
            3. Subject line patterns and categories
            4. Response time patterns
            5. Recommendations for better email management
            """
        elif insight_type == "cleanup":
            prompt = """
            Analyze emails for cleanup opportunities:
            1. Identify potential spam/junk patterns
            2. Find unsubscribe opportunities
            3. Suggest archival candidates
            4. Recommend organization improvements
            """
        elif insight_type == "security":
            prompt = """
            Analyze emails for security concerns:
            1. Identify potentially suspicious senders
            2. Find phishing attempt patterns
            3. Highlight unusual access patterns
            4. Security recommendations
            """
        else:
            prompt = f"Analyze emails for {insight_type} insights and provide actionable recommendations."
        
        context = self._prepare_email_context(emails, 30)  # Use 30 days of context
        
        try:
            insights_text = await provider.generate_summary(prompt, context)
            return {
                "insight_type": insight_type,
                "insights": insights_text,
                "email_count": len(emails),
                "generated_at": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to generate insights: {e}")
            return {
                "error": str(e),
                "insight_type": insight_type,
                "email_count": len(emails)
            }