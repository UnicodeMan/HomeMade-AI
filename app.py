import os
import google.generativeai as genai
import uvicorn
import asyncio
from fastapi import FastAPI, WebSocket, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import  Dict
from datetime import datetime
import json
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
import signal
import sys
import sys
from contextlib import asynccontextmanager
from lib.endpoints import mainRouter, sessionRouter, modelRouter
from lib.shell_environment import ShellEnvironment 
from lib.ai_generation import generate_content_with_limit
from lib.chat_history import ChatContext
from lib.limiter import RateLimiter
from lib.ai_model import AIModelFactory, GeminiAI, HuggingFaceAI
import atexit

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


class GlobalState:
    def __init__(self):
        self.shell_env = None
        self.chat_context = None
        self.active_websockets: Dict[str, WebSocket] = {}

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
global shell_env  # Make shell_env globally accessible



MAX_CALLS=9



# FastAPI app setup with proper lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize semaphore
    app.state.MAX_CALLS=9

    app.state.semaphore = asyncio.Semaphore(app.state.MAX_CALLS)
    app.state.chat_context = ChatContext()
    app.state.global_state = GlobalState()
    app.state.shell_env = ShellEnvironment()

    def on_exit():
        print("Application is exiting, saving chat history to database...")
        app.state.chat_context.save_history_to_db()

    atexit.register(on_exit)
    app.state.rate_limiter = RateLimiter()
    await app.state.rate_limiter.init_redis()    # Configure Google Generative AI
    
    # Get API key from environment
    api_key = os.getenv("GENAI_API_KEY")
    if not api_key:
        raise ValueError("GENAI_API_KEY not found")

    # Register available model providers
    AIModelFactory.register_model("gemini", GeminiAI)
    AIModelFactory.register_model("huggingface", HuggingFaceAI)
    # Register other providers here...

    try:
        # Initialize with default model
        model_instance, available_models = await AIModelFactory.create(
            api_key=api_key,
            model_name="gemini-2.0-flash-exp"  # Default model
        )
        
        app.state.model = model_instance
        app.state.available_models = available_models
        
    except Exception as e:
        print(f"Error initializing default model: {str(e)}")
        raise
    # Startup logic
    try:
        print("Entering startup_event function")
        response = await generate_content_with_limit(
            app.state.model,
            input_text=app.state.chat_context.system_prompt,
            temperature=0.7,
            semaphore=app.state.semaphore
        )
        await app.state.chat_context.save_chat_message("system_prompt", app.state.chat_context.system_prompt)
        initial_ai_response = response.content
        if response and hasattr(response, "content"):
            initial_ai_response = response.content
            await app.state.chat_context.save_chat_message("assistant", initial_ai_response)
            print("Initial message sent and saved to chat history.")
            print(f"Response: {initial_ai_response}")
        else:
            print("Failed to generate initial message.")

    except Exception as e:
        print(f"Error generating response: {e}")

    yield  # This marks the end of the startup phase

    # Cleanup logic
    if app.state.global_state.shell_env:
        app.state.global_state.shell_env.reset_shell("all")
    await app.state.rate_limiter.close_redis()  # Cleanup Redis connection


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your actual frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.mount("/static", StaticFiles(directory="static"), name="static")



def signal_handler(signum, frame):
    raise KeyboardInterrupt("Command execution interrupted")
signal.signal(signal.SIGINT, signal_handler)  # Register the handler


app.include_router(sessionRouter)
app.include_router(modelRouter, prefix="/models")
app.include_router(mainRouter)

@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


# Initialize a counter for API requests
api_request_count = 0
def format_sse_event(data):
    return f"data: {json.dumps(data)}\n\n"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        ws_max_size=64777216,  # ~60MB max WebSocket message size
        ws_ping_interval=30,    # Send ping every 30 seconds
        ws_ping_timeout=10,     # Wait 10 seconds for pong before closing
        log_level="trace"
    )
