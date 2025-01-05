from huggingface_hub import InferenceClient, HfApi, model_info
import aiohttp
import asyncio
import json
from typing import Dict, List, Optional, Any
from .base_model import AIModel
from ..models import ModelInfo, ModelResponse, QuotaInfo, ModelResponseType, QuotaInfo, ModelLimits
import time
import traceback
import sys
import json
class HuggingFaceAI(AIModel):
    """HuggingFace AI implementation using Inference API"""
    
    def __init__(self):
        self.client = None
        self.hf_api = None
        self.api_key = None
        self.model_name = None
        self.default_model = "mistralai/Mistral-7B-Instruct-v0.1"
        self._quota_cache = None
        self._quota_cache_time = None
        self._quota_cache_duration = 300  # 5 minutes
        self.model_name = "Class instance is not initialized"
        self.provider = "huggingface"
    async def initialize(self, api_key: str, model_name: Optional[str] = None, **kwargs) -> None:
        """Initialize HuggingFace client and model"""
        self.api_key = api_key
        self.hf_api = HfApi(token=api_key)
        
        try:
            self.model_name = model_name or self.default_model
            print(f"Initializing HuggingFace model: {self.model_name}", file=sys.stderr)
        
            # Initialize the inference client
            self.model_name = model_name or self.default_model
            self.client = InferenceClient(
                model=self.model_name,
                token=api_key
            )
            
            # Verify model exists and is available for inference
            model = model_info(self.model_name, token=api_key)
            if not model.pipeline_tag:
                raise ValueError(f"Model {self.model_name} doesn't support inference API")
                
        except Exception as e:
            raise ValueError(f"Failed to initialize HuggingFace model: {str(e)}")
    async def get_provider(self):
        return self.provider
    async def get_model_name(self):
        return self.model_name
    async def get_available_models(self) -> List[ModelInfo]:
        """Get available HuggingFace models with inference API enabled"""
        try:
            # Filter for models that support inference API
            models = self.hf_api.list_models(
                task="text-generation",
                library="transformers",
                limit=10
            )
            
            model_info_list = []
            for model in models:
                # Get detailed model information
                details = model_info(model.modelId, token=self.api_key)
                """
                status = await self.check_model_status(model.modelId)
                print(f"Model status: {status}")
                if status.get("state") != "loaded" or status.get("state") != "loading":
                    continue
                """
                print(f"Model details: {details}", file=sys.stderr)
                # Extract supported features
                features = []
                if details.pipeline_tag:
                    features.append(details.pipeline_tag)
                if details.library_name:
                    features.append(f"library:{details.library_name}")
                #print(details)
                description = getattr(details, 'description', '')
                config = details.config or {}
                max_tokens = config.get("max_position_embeddings") or config.get("max_length") or config.get("max_tokens") or 2048

                info = ModelInfo(
                    name=model.modelId,
                    max_tokens=max_tokens,
                    description=description,
                    supported_features=features,
                    provider="huggingface"
                )
                model_info_list.append(info)
            
            return model_info_list
            
        except Exception as e:
            print(f"Error fetching HuggingFace models: {str(e)}")
            return []

    async def get_quota_info(self) -> Optional[QuotaInfo]:
        """Get quota information from HuggingFace API"""
        try:
            # Check if we have cached quota info that's still valid
            if (self._quota_cache and self._quota_cache_time and 
                (time.time() - self._quota_cache_time) < self._quota_cache_duration):
                return self._quota_cache

            # Fetch current quota usage
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api-inference.huggingface.co/quota",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        quota_info = QuotaInfo(
                            requests_per_minute=data.get("rate_limit", {}).get("requests", None),
                            tokens_per_minute=data.get("rate_limit", {}).get("tokens", None),
                            remaining_requests=data.get("remaining", {}).get("requests", None),
                            remaining_tokens=data.get("remaining", {}).get("tokens", None)
                        )
                        print(quota_info)
                        # Cache the quota info
                        self._quota_cache = quota_info
                        self._quota_cache_time = time.time()
                        
                        return quota_info
            
            return None
        except Exception as e:
            print(f"Error fetching quota info: {str(e)}")
            return None
    async def check_model_status(self, model_name: str) -> Dict[str, Any]:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api-inference.huggingface.co/status/models/{model_name}",
                headers={"Authorization": f"Bearer {self.api_key}"}
            ) as response:
                return await response.json()
    async def generate_content(self,
                         prompt: list,
                         max_tokens: Optional[int] = 8096,
                         temperature: Optional[float] = 0.7,
                         **kwargs) -> ModelResponse:
        """Generate content using HuggingFace model with proper async handling"""
        processed_prompt = []
        for message in prompt:
            if isinstance(message, dict) and "content" in message:
                original_role = message.get("role")
                if original_role in ("command", "user", "system_prompt"):  # Roles to map to "user"
                    new_role = "user"
                elif original_role in ("assistant", "assistant_response_command"):  # Roles to map to "model"
                    new_role = "assistant"
                elif original_role in ("system"): # Roles to skip
                    continue  # Skip system messages
                else:
                    new_role = "user"  # Default to "user" for unknown roles


                processed_prompt.append({
                    "role": new_role,  # Get role, handle if missing
                    "content": message["content"]
                })
        #jsonified = json.dumps(processed_prompt)
        #print(f"Formatted prompt: {jsonified}", file=sys.stderr)
        try:
            if not self.client:
                raise ValueError("Model not initialized")

            # Prepare parameters
            params = {
                "max_tokens": max_tokens,
                "temperature": temperature,
                "do_sample": True,
                **kwargs
            }

            # Remove None values
            params = {k: v for k, v in params.items() if k != "do_sample" and v is not None}
            completion = None
            completion = self.client.chat.completions.create(
                messages=processed_prompt,
                **params
            )
            print(completion)

            return ModelResponse(
                type=ModelResponseType.TEXT,
                content=completion.choices[0].message.content,
                raw_response=completion
            )

        except Exception as e:
            traceback.print_exc()
            print(f"The error is this: {str(e)}", file=sys.stderr)
            content = "Error without a message"
            if hasattr(completion, 'choices') and completion.choices and hasattr(completion.choices[0], 'message') and hasattr(completion.choices[0].message, 'content'):
                content = completion.choices[0].message.content
            print(f'{content=}', file=sys.stderr)
            return ModelResponse(
                type=ModelResponseType.ERROR,
                content=content,
                error=str(e),
                raw_response=None
            )
    def format_prompt_for_inference_api(self, prompt: List[Dict[str, str]]) -> str:
      """Formats the prompt for the Hugging Face Inference API."""
      # Combine all messages into a single string for the Inference API
      formatted_prompt = ""
      for message in prompt:
          # This is a simplified formatting. You might need to adjust it
          # based on the specific model you are using.
          if message["role"] == "user":
              formatted_prompt += f"{message['content']} "
          elif message["role"] == "assistant":
              formatted_prompt += f"{message['content']} "

      return formatted_prompt.strip()

    async def validate_api_key(self, api_key: str) -> bool:
        """Validate HuggingFace API key using huggingface_hub."""
        try:
            api = HfApi(token=api_key)
            #  A simple API call to test the connection
            api.whoami()  
            return True
        except Exception:
            traceback.print_exc()
            return False
    async def get_rate_per_minute(self) -> int:
        """Get the RPM of the model"""
        return 15 # dummy value
    async def get_rate_per_day(self) -> int:
        """Get the RPD of the model"""
        return 1000 # dummy value