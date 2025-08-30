"""Unit tests for AIService."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from kit_gmail.services.ai_service import AIService, AnthropicProvider, OpenAIProvider, XAIProvider


class TestAnthropicProvider:
    
    @pytest.fixture
    def provider(self, mock_anthropic_client):
        """Anthropic provider with mocked client."""
        with patch('anthropic.Anthropic', return_value=mock_anthropic_client):
            return AnthropicProvider("test-api-key")
    
    @pytest.mark.asyncio
    async def test_generate_summary(self, provider, mock_anthropic_client):
        """Test summary generation."""
        prompt = "Summarize these emails"
        context = "Email 1: Test email content"
        
        result = await provider.generate_summary(prompt, context)
        
        assert result == "Test AI response"
        mock_anthropic_client.messages.create.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_analyze_email(self, provider, mock_anthropic_client, sample_processed_email):
        """Test email analysis."""
        # Mock response with JSON content
        mock_message = Mock()
        mock_message.content = [Mock(text='{"sentiment": "positive", "category": "personal"}')]
        mock_anthropic_client.messages.create.return_value = mock_message
        
        result = await provider.analyze_email(sample_processed_email)
        
        assert isinstance(result, dict)
        assert "sentiment" in result or "analysis" in result  # Either parsed JSON or raw text


class TestOpenAIProvider:
    
    @pytest.fixture
    def provider(self, mock_openai_client):
        """OpenAI provider with mocked client."""
        with patch('openai.AsyncOpenAI', return_value=mock_openai_client):
            return OpenAIProvider("test-api-key")
    
    @pytest.mark.asyncio
    async def test_generate_summary(self, provider, mock_openai_client):
        """Test summary generation."""
        mock_openai_client.chat.completions.create = AsyncMock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Test AI response"))]
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        prompt = "Summarize these emails"
        context = "Email 1: Test email content"
        
        result = await provider.generate_summary(prompt, context)
        
        assert result == "Test AI response"
        mock_openai_client.chat.completions.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_email(self, provider, mock_openai_client, sample_processed_email):
        """Test email analysis."""
        mock_openai_client.chat.completions.create = AsyncMock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='{"sentiment": "neutral"}'))]
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        result = await provider.analyze_email(sample_processed_email)
        
        assert isinstance(result, dict)
        assert "sentiment" in result or "analysis" in result


class TestXAIProvider:
    
    @pytest.fixture
    def provider(self):
        """XAI provider with mocked client."""
        return XAIProvider("test-api-key")
    
    @pytest.mark.asyncio
    async def test_generate_summary(self, provider):
        """Test summary generation."""
        with patch.object(provider.client, 'post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Test AI response"}}]
            }
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response
            
            prompt = "Summarize these emails"
            context = "Email 1: Test email content"
            
            result = await provider.generate_summary(prompt, context)
            
            assert result == "Test AI response"
            mock_post.assert_called_once_with(
                "/chat/completions", 
                json=pytest.approx({
                    "model": "grok-beta",
                    "messages": [
                        {"role": "system", "content": pytest.any_string_},
                        {"role": "user", "content": f"{prompt}\n\nContext:\n{context}"}
                    ],
                    "max_tokens": 1000,
                    "temperature": 0.3
                }, rel=1e-9)
            )


class TestAIService:
    
    @pytest.fixture
    def ai_service(self):
        """AIService instance."""
        return AIService()
    
    def test_initialize_providers(self):
        """Test provider initialization."""
        with patch('kit_gmail.utils.config.settings') as mock_settings:
            mock_settings.anthropic_api_key = "test-key"
            mock_settings.openai_api_key = None
            mock_settings.xai_api_key = None
            
            service = AIService()
            
            assert "anthropic" in service.providers
            assert "openai" not in service.providers
            assert "xai" not in service.providers
    
    def test_get_provider_default(self, ai_service):
        """Test getting default provider."""
        # Mock a provider
        mock_provider = Mock()
        ai_service.providers["test_provider"] = mock_provider
        
        with patch('kit_gmail.utils.config.settings') as mock_settings:
            mock_settings.default_ai_service = "test_provider"
            
            provider = ai_service.get_provider()
            assert provider == mock_provider
    
    def test_get_provider_fallback(self, ai_service):
        """Test provider fallback when requested provider not available."""
        mock_provider = Mock()
        ai_service.providers["available_provider"] = mock_provider
        
        # Request non-existent provider
        provider = ai_service.get_provider("non_existent")
        assert provider == mock_provider
    
    def test_get_provider_none_available(self, ai_service):
        """Test error when no providers available."""
        ai_service.providers = {}
        
        with pytest.raises(RuntimeError, match="No AI providers available"):
            ai_service.get_provider()
    
    def test_prepare_email_context(self, ai_service, sample_processed_email):
        """Test email context preparation."""
        # Create different types of emails
        emails = [sample_processed_email]
        
        # Mark as different types
        sample_processed_email.is_critical = True
        
        context = ai_service._prepare_email_context(emails, 7)
        
        assert "Email Summary for 7 days" in context
        assert "CRITICAL EMAILS" in context
        assert sample_processed_email.subject in context
        assert sample_processed_email.sender in context
    
    def test_create_summary_prompt(self, ai_service):
        """Test summary prompt creation."""
        prompt = ai_service._create_summary_prompt("daily", 7, 100)
        
        assert "100 emails" in prompt
        assert "7 days" in prompt
        assert "daily" in prompt
        assert "Overview" in prompt
        assert "Action Items" in prompt
    
    @pytest.mark.asyncio
    async def test_generate_email_summary(self, ai_service, sample_processed_email):
        """Test email summary generation."""
        # Mock provider
        mock_provider = AsyncMock()
        mock_provider.generate_summary.return_value = "Test summary"
        ai_service.providers["test"] = mock_provider
        
        with patch('kit_gmail.utils.config.settings') as mock_settings:
            mock_settings.default_ai_service = "test"
            
            emails = [sample_processed_email]
            result = await ai_service.generate_email_summary(emails, 7, "daily")
            
            assert result == "Test summary"
            mock_provider.generate_summary.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_email_summary_no_emails(self, ai_service):
        """Test summary generation with no emails."""
        result = await ai_service.generate_email_summary([], 7, "daily")
        assert "No emails found" in result
    
    @pytest.mark.asyncio
    async def test_analyze_batch_emails(self, ai_service, sample_processed_email):
        """Test batch email analysis."""
        # Mock provider
        mock_provider = AsyncMock()
        mock_provider.analyze_email.return_value = {"sentiment": "positive"}
        ai_service.providers["test"] = mock_provider
        
        with patch('kit_gmail.utils.config.settings') as mock_settings:
            mock_settings.default_ai_service = "test"
            
            emails = [sample_processed_email] * 3
            results = await ai_service.analyze_batch_emails(emails)
            
            assert len(results) == 3
            assert all("sentiment" in r for r in results)
            assert all("email_id" in r for r in results)
    
    @pytest.mark.asyncio
    async def test_get_email_insights(self, ai_service, sample_processed_email):
        """Test email insights generation."""
        # Mock provider
        mock_provider = AsyncMock()
        mock_provider.generate_summary.return_value = "Test insights"
        ai_service.providers["test"] = mock_provider
        
        with patch('kit_gmail.utils.config.settings') as mock_settings:
            mock_settings.default_ai_service = "test"
            
            emails = [sample_processed_email]
            result = await ai_service.get_email_insights(emails, "patterns")
            
            assert result["insight_type"] == "patterns"
            assert result["insights"] == "Test insights"
            assert result["email_count"] == 1
            assert "generated_at" in result