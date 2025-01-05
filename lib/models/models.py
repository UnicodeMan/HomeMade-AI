from pydantic import BaseModel
from typing import Optional, List
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any, Type

class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    command_output: Optional[str] = None


class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: str

class ChatHistory(BaseModel):
    messages: List[ChatMessage]
@dataclass
class ModelInfo:
    """Data class to store model information consistently across different APIs"""
    name: str
    max_tokens: int
    description: str = ""
    rate_limit: Optional[int] = None  # requests per minute
    supported_features: List[str] = None
    provider: str = ""  # e.g., "gemini", "openai", "anthropic"

    def __post_init__(self):
        if self.supported_features is None:
            self.supported_features = []
            

class ModelLimits:
    def __init__(self, data: dict):
        for key, value in data.items():
            if isinstance(value, dict):
                setattr(self, key, ModelLimits(value))  # Recursively create ModelLimits objects for nested dicts
            else:
                setattr(self, key, value)
class ModelResponseType(Enum):
    TEXT = "text"
    JSON = "json"
    ERROR = "error"

@dataclass
class ModelResponse:
    """Standardized response format for all AI models"""
    type: ModelResponseType
    content: str
    error: Optional[str] = None
    raw_response: Any = None

@dataclass
class QuotaInfo:
    """Data class to store API quota information"""
    requests_per_minute: Optional[int] = None
    requests_per_day: Optional[int] = None
    tokens_per_minute: Optional[int] = None
    tokens_per_day: Optional[int] = None
    remaining_requests: Optional[int] = None
    remaining_tokens: Optional[int] = None