from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Type
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
import os
import asyncio
from enum import Enum
from typing import Tuple
import sys
from ..models import ModelInfo, ModelResponse, QuotaInfo, ModelResponseType, QuotaInfo, ModelLimits
class AIModelFactory:
    """Factory for creating AI model instances"""
    _models: Dict[str, Type['AIModel']] = {}
    _provider_models: Dict[str, List[ModelInfo]] = {}
    _initialized_providers: Dict[str, bool] = {}
    
    @classmethod
    def register_model(cls, provider: str, model_class: Type['AIModel']):
        """Register a model class with its provider"""
        cls._models[provider] = model_class
        cls._initialized_providers[provider] = False
        cls._provider_models[provider] = []
    
    @classmethod
    async def initialize_provider(cls, provider: str, api_key: str) -> List[ModelInfo]:
        """Initialize a specific provider and fetch its models"""
        if provider not in cls._models:
            raise ValueError(f"Provider {provider} not registered")
        
        if not cls._initialized_providers[provider]:
            instance = cls._models[provider]()
            try:
                # Validate API key first
                is_valid = await instance.validate_api_key(api_key)
                if not is_valid:
                    raise ValueError(f"Invalid API key for provider {provider}")
                
                # Initialize the instance
                await instance.initialize(api_key)
                
                # Fetch available models and quotas
                models = await instance.get_available_models()
                quota = await instance.get_quota_info()
                
                # Update models with quota information if available
                for model in models:
                    if quota and quota.requests_per_minute:
                        model.rate_limit = quota.requests_per_minute
                    model.provider = provider
                
                cls._provider_models[provider] = models
                cls._initialized_providers[provider] = True
            except Exception as e:
                raise ValueError(f"Failed to initialize provider {provider}: {str(e)}")
        
        return cls._provider_models[provider]
    
    @classmethod
    async def get_available_providers(cls) -> List[str]:
        """Get list of registered providers"""
        return list(cls._models.keys())
    
    @classmethod
    async def get_provider_models(cls, provider: str, api_key: str) -> List[ModelInfo]:
        """Get available models for a specific provider"""
        return await cls.initialize_provider(provider, api_key)
    
    @classmethod
    def get_provider_for_model(cls, model_name: str) -> Optional[str]:
        """Determine the provider based on model name"""
        model_prefixes = {
            "gemini": "gemini",
            "gpt": "openai",
            "claude": "anthropic",
        }
        
        for prefix, provider in model_prefixes.items():
            if model_name.lower().startswith(prefix):
                return provider
        return None
    
    @classmethod
    async def create(cls, api_key: str, provider: str = "gemini", model_name: Optional[str] = None) -> tuple['AIModel', List[ModelInfo]]:
        model_class = cls._models.get(provider)
        if not model_class:
            raise ValueError(f"Unknown AI model provider: {provider}")

        model_instance = model_class()
        await model_instance.initialize(api_key=api_key)

        available_models = await model_instance.get_available_models()
        full_model_name = model_name or model_instance.default_model
        if model_name:
            model_exists = any(model.name == model_name for model in available_models)
            print(f"Trying to use model: {full_model_name}")
            # If not found, raise the error
            if not model_exists:
                print(f"Model {model_name} not found in available models for {provider}, using default model", file=sys.stderr)
                full_model_name = model_instance.default_model
            else:
                print(f"Using model: {full_model_name}")
            # Pass the correct model_name to initialize method
            await model_instance.initialize(api_key=api_key, model_name=full_model_name)
        return model_instance, available_models


class AIModel(ABC):
    """Abstract base class for AI model implementations"""
    
    @abstractmethod
    async def initialize(self, api_key: str, model_name: Optional[str] = None, **kwargs) -> None:
        """Initialize the model with API key and optional model name"""
        pass
    
    @abstractmethod
    async def get_available_models(self) -> List[ModelInfo]:
        """Retrieve list of available models"""
        pass
    
    @abstractmethod
    async def generate_content(self, 
                             prompt: list, 
                             max_tokens: Optional[int] = None,
                             temperature: Optional[float] = None,
                             **kwargs) -> ModelResponse:
        """Generate content from the model"""
        pass
    
    @abstractmethod
    async def get_quota_info(self) -> Optional[QuotaInfo]:
        """Get quota information for the API key"""
        pass
    
    @abstractmethod
    async def validate_api_key(self, api_key: str) -> bool:
        """Validate if the API key is correct"""
        pass
    @abstractmethod
    async def get_model_name(self) -> str:
        """Get the name of the model"""
        pass
    @abstractmethod
    async def get_provider(self) -> str:
        """Get the provider of the model"""
        pass
    @abstractmethod
    async def get_rate_per_minute(self) -> int:
        """Get the RPM of the model"""
        pass
    @abstractmethod
    async def get_rate_per_day(self) -> int:
        """Get the RPD of the model"""
        pass