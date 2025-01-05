
from fastapi import APIRouter, HTTPException, Request
from typing import Optional, List
from pydantic import BaseModel
import os
from ..ai_model import AIModelFactory, GeminiAI
import traceback
modelRouter = APIRouter()

class ModelSwitchRequest(BaseModel):
    model_name: str
    api_key: Optional[str] = None
    provider: Optional[str] = None

class ModelInfo(BaseModel):
    name: str
    provider: str
    description: Optional[str] = None
    supported_features: List[str] = []

@modelRouter.post("/switch-model")
async def switch_model(request: Request, model_switch_request: ModelSwitchRequest):
    try:
        # Get the application state
        app = request.app
        api_key = None
        if(model_switch_request.provider == "gemini"):
            api_key = os.getenv("GENAI_API_KEY")
        if(model_switch_request.provider == "huggingface"):
            api_key = os.getenv("HF_API_KEY")
        if(model_switch_request.provider == "anthropic"):
            api_key = os.getenv("ANTHROPIC_API_KEY")
        if(model_switch_request.provider == "openai"):
            api_key = os.getenv("OPENAI_API_KEY")
            
        # Use factory to create new model instance
        model_instance, available_models = await AIModelFactory.create(
            api_key=api_key,
            model_name=model_switch_request.model_name,
            provider=model_switch_request.provider
        )
        
        # Update the application state with new model
        request.app.state.model = model_instance
        
        return {
            "status": "success",
            "message": f"Switched to model: {model_switch_request.model_name}",
            "available_models": [
                ModelInfo(
                    name=model.name,
                    provider=model.provider,
                    description=model.description,
                    supported_features=model.supported_features
                ).json()
                for model in available_models
            ]
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

@modelRouter.get("/available-models")
async def get_available_models():
    try:
        app = modelRouter.app
        api_keys = {
            "gemini": os.getenv("GENAI_API_KEY"),
            "huggingface": os.getenv("HF_API_KEY"),
            "anthropic": os.getenv("ANTHROPIC_API_KEY"),
            "openai": os.getenv("OPENAI_API_KEY")
        }
        print(f"hf_key: {api_keys['huggingface']}")
        # Get all available providers
        providers = await AIModelFactory.get_available_providers()
        print(providers)
        # Get models for each provider
        all_models = []
        for provider in providers:
            try:
                provider_models = await AIModelFactory.get_provider_models(
                    provider=provider,
                    api_key=api_keys[provider]
                )
                all_models.extend(provider_models)
            except Exception as e:
                traceback.print_exc()
                print(f"Error getting models for provider {provider}: {str(e)}")
                continue
        
        return {
            "models": [
                ModelInfo(
                    name=model.name,
                    provider=model.provider,
                    description=model.description,
                    supported_features=model.supported_features
                ).json()
                for model in all_models
            ]
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))