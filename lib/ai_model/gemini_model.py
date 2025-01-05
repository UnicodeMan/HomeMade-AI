from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Type
from dataclasses import dataclass
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
import os
import json
import asyncio
from enum import Enum
from .base_model import AIModel
from ..models import ModelInfo, ModelResponse, QuotaInfo, ModelResponseType, QuotaInfo, ModelLimits
import sys

class GeminiAI(AIModel):
    """Gemini AI implementation"""

    def __init__(self):
        self.model = None
        self.api_key = None
        self.default_model = "gemini-2.0-flash-exp"
        self.model_name = "Class instace is not initialized"
        self.provider = "gemini"
    async def initialize(self, api_key: str, model_name: Optional[str] = None, limits_file="lib/ai_model/gemini_model_info.json", **kwargs) -> None:
        """Initialize Gemini API and model"""
        self.api_key = api_key
        genai.configure(api_key=api_key)
        self.limits = None

        try:
            if model_name:
                self.model = genai.GenerativeModel(model_name)
                self.model_name = model_name
            else:
                return
            try:
                with open(limits_file, "r") as f:
                    limits_data = json.load(f)
                if self.model_name in limits_data:
                    print(f"Model name that will be searched in json file: {self.model_name}", file=sys.stderr)
                    #print(f"Initial limits data: {json.dumps(limits_data, )}", file=sys.stderr)
                    model_data = limits_data.get(self.model_name, {})
                    #print("Model data: ", json.dumps(model_data), file=sys.stderr)
                    self.limits = ModelLimits(model_data)  # Create and assign the limits object. ensures the structure with sub-categories
                    print(f"Limits loaded for model: {self.model_name}", file=sys.stderr)
                    print(f"RPM: {self.limits.ratelimit.requests_per_minute}", file=sys.stderr)
                else:
                    print(f"Warning: No limits found in '{limits_file}' for model '{self.model_name}'. Limits not loaded.")
            except FileNotFoundError:
                print(f"Warning: Limits file '{limits_file}' not found. Limits not loaded.")
            except json.JSONDecodeError:
                print(f"Warning: Invalid JSON in '{limits_file}'. Limits not loaded.")
        except Exception as e:
            raise ValueError(f"Failed to initialize Gemini model: {str(e)}")
    async def get_provider(self) -> str:
        return self.provider
    async def get_model_name(self) -> str:
        return self.model_name
    async def get_available_models(self) -> List[ModelInfo]:
        """Get available Gemini models"""
        try:
            loop = asyncio.get_event_loop()
            models = await loop.run_in_executor(None, genai.list_models)
            return [
                ModelInfo(
                    name=model.name[7:] if "models/" in model.name else model.name,
                    max_tokens=model.output_token_limit,
                    description=getattr(model, 'description', ''),
                    supported_features=[
                        feature for feature in ['text', 'images', 'chat']
                        if hasattr(model, feature) and getattr(model, feature)
                    ],
                    provider="gemini"
                )
                for model in models
            ]
        except Exception as e:
            print(f"Error fetching Gemini models: {str(e)}")
            return []

    async def get_quota_info(self) -> Optional[QuotaInfo]:
        """Get quota information for Gemini API"""
        try:
            # Note: As of now, Gemini API doesn't provide direct quota info
            # This is a placeholder for when the feature becomes available
            # For now, returning default values
            return QuotaInfo(
                requests_per_minute=15,  # Default value
                requests_per_day=None,
                tokens_per_minute=None,
                tokens_per_day=None,
                remaining_requests=None,
                remaining_tokens=None
            )
        except Exception:
            return None

    async def generate_content(self,
                             prompt: list,
                             max_tokens: Optional[int] = 8192,
                             temperature: Optional[float] = 0.89,
                             **kwargs) -> ModelResponse:
        """Generate content using Gemini"""
        processed_prompt = []
        print(prompt)
        for message in prompt:
            if isinstance(message, dict) and "content" in message:
                original_role = message.get("role")
                if original_role in ("command", "user", "system_prompt"):  # Roles to map to "user"
                    new_role = "user"
                elif original_role in ("assistant", "assistant_response_command"):  # Roles to map to "model"
                    new_role = "model"
                elif original_role in ("system"): # Roles to skip
                    continue  # Skip system messages
                else:
                    new_role = "user"  # Default to "user" for unknown roles


                processed_prompt.append({
                    "role": new_role,  # Get role, handle if missing
                    "parts": [{"text": message["content"]}]
                })
        #print("Processed Prompt: ", processed_prompt)
        try:
            if not self.model:
                raise ValueError("Model not initialized")

            generation_config = GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
                **kwargs  # Pass any extra kwargs to generation_config
            )

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(
                    processed_prompt,
                    generation_config=generation_config
                )
            )
            #print("Response: ", response)
            # Correctly extract text from response
            if response.candidates:
                text_content = response.candidates[0].content.parts[0].text
            else:
                text_content = ""  # Or raise an exception if you prefer

            return ModelResponse(
                type=ModelResponseType.TEXT,
                content=text_content,
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
        """Validate Gemini API key"""
        try:
            genai.configure(api_key=api_key)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, genai.list_models)
            return True
        except Exception:
            return False
    async def get_rate_per_minute(self) -> int:
        """Get the RPM of the model"""
        if self.limits is not None:
            return self.limits.ratelimit.requests_per_minute
        else:
            return 2
    async def get_rate_per_day(self) -> int:
        """Get the RPD of the model"""
        if self.limits is not None:
            return self.limits.ratelimit.requests_per_day
        else:
            return 50
