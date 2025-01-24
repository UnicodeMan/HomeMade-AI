from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Type
from anthropic import Anthropic, AsyncAnthropic, HUMAN_PROMPT, AI_PROMPT
from ..models import ModelInfo, ModelResponse, QuotaInfo, ModelResponseType, QuotaInfo, ModelLimits
import asyncio
import sys

class ClaudeAI(AIModel):
    """Claude AI implementation"""

    def __init__(self):
        self.client = None
        self.api_key = None
        self.default_model = "claude-3-sonnet-20240229"
        self.model_name = "Class instance is not initialized"
        self.provider = "anthropic"
        self.model_limits = None

    async def initialize(self, api_key: str, model_name: Optional[str] = None, **kwargs) -> None:
        """Initialize Claude API and model"""
        self.api_key = api_key
        self.client = AsyncAnthropic(api_key=api_key)
        
        try:
            if model_name:
                self.model_name = model_name
            else:
                self.model_name = self.default_model
                
            # Query model limits from API
            model_info = await self.get_model_info()
            if model_info:
                self.model_limits = model_info
            
        except Exception as e:
            raise ValueError(f"Failed to initialize Claude model: {str(e)}")

    async def get_model_info(self) -> Optional[ModelLimits]:
        """Get model information and limits from Anthropic API"""
        try:
            # These are example values - in practice you'd query the Anthropic API
            # Note: As of now, Anthropic doesn't provide a direct API endpoint for this
            limits = {
                "claude-3-opus-20240229": {"rpm": 5, "rpd": 500, "max_tokens": 4096},
                "claude-3-sonnet-20240229": {"rpm": 5, "rpd": 500, "max_tokens": 4096},
                "claude-3-haiku-20240307": {"rpm": 5, "rpd": 500, "max_tokens": 4096}
            }
            
            if self.model_name in limits:
                model_data = limits[self.model_name]
                return ModelLimits({
                    "ratelimit": {
                        "requests_per_minute": model_data["rpm"],
                        "requests_per_day": model_data["rpd"]
                    },
                    "context": {
                        "max_tokens": model_data["max_tokens"]
                    }
                })
            return None
        except Exception as e:
            print(f"Error fetching model info: {str(e)}", file=sys.stderr)
            return None

    async def get_available_models(self) -> List[ModelInfo]:
        """Get available Claude models"""
        try:
            # These would ideally come from an API endpoint
            models = [
                {
                    "name": "claude-3-opus-20240229",
                    "max_tokens": 4096,
                    "description": "Most capable Claude model, ideal for complex tasks",
                },
                {
                    "name": "claude-3-sonnet-20240229",
                    "max_tokens": 4096,
                    "description": "Balanced model for most tasks",
                },
                {
                    "name": "claude-3-haiku-20240307",
                    "max_tokens": 4096,
                    "description": "Fastest Claude model for simple tasks",
                }
            ]
            
            return [
                ModelInfo(
                    name=model["name"],
                    max_tokens=model["max_tokens"],
                    description=model["description"],
                    supported_features=["text", "chat"],
                    provider=self.provider
                )
                for model in models
            ]
        except Exception as e:
            print(f"Error fetching Claude models: {str(e)}")
            return []

    async def get_quota_info(self) -> Optional[QuotaInfo]:
        """Get quota information for Claude API"""
        if self.model_limits:
            return QuotaInfo(
                requests_per_minute=self.model_limits.ratelimit.requests_per_minute,
                requests_per_day=self.model_limits.ratelimit.requests_per_day,
                tokens_per_minute=None,
                tokens_per_day=None,
                remaining_requests=None,
                remaining_tokens=None
            )
        return None

    async def generate_content(self,
                             prompt: list,
                             max_tokens: Optional[int] = None,
                             temperature: Optional[float] = 0.7,
                             **kwargs) -> ModelResponse:
        """Generate content using Claude"""
        try:
            if not self.client:
                raise ValueError("Model not initialized")

            # Process the messages into Claude format
            messages = []
            for msg in prompt:
                if isinstance(msg, dict) and "content" in msg:
                    role = msg.get("role", "user")
                    if role in ("command", "user", "system_prompt"):
                        messages.append({"role": "user", "content": msg["content"]})
                    elif role in ("assistant", "assistant_response_command"):
                        messages.append({"role": "assistant", "content": msg["content"]})
                    # Skip system messages as they should be incorporated into the first user message

            response = await self.client.messages.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )

            return ModelResponse(
                type=ModelResponseType.TEXT,
                content=response.content[0].text,
                raw_response=response
            )

        except Exception as e:
            return ModelResponse(
                type=ModelResponseType.ERROR,
                content="",
                error=str(e),
                raw_response=None
            )

    async def validate_api_key(self, api_key: str) -> bool:
        """Validate Claude API key"""
        try:
            client = AsyncAnthropic(api_key=api_key)
            # Simple validation request
            await client.messages.create(
                model="claude-3-haiku-20240307",
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=1
            )
            return True
        except Exception:
            return False

    async def get_provider(self) -> str:
        return self.provider

    async def get_model_name(self) -> str:
        return self.model_name

    async def get_rate_per_minute(self) -> int:
        if self.model_limits:
            return self.model_limits.ratelimit.requests_per_minute
        return 5  # Default fallback value

    async def get_rate_per_day(self) -> int:
        if self.model_limits:
            return self.model_limits.ratelimit.requests_per_day
        return 500  # Default fallback value