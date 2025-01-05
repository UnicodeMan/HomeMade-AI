import os
from lib.utils import utils
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi import Query
from fastapi import APIRouter, Request
import asyncio
import json
import sys
import traceback
from ..limiter import RateLimiter
from ..chat_history import ChatContext
from ..ai_generation import process_response_recursively
from ..ai_model import AIModel
from datetime import datetime
mainRouter = APIRouter()

@mainRouter.get("/", response_class=HTMLResponse)
async def home():
    """Serve the chat interface."""
    with open("static/index.html", "r") as f:
        html_content = f.read()
    return html_content

@mainRouter.websocket("/chat")
async def websocket_endpoint(websocket: WebSocket):
    print("In websocket /chat endpoint.")  # Keep only one print statement

    await websocket.accept()

    chat_context: ChatContext = websocket.app.state.chat_context
    rate_limiter: RateLimiter = websocket.app.state.rate_limiter
    model: AIModel = websocket.app.state.model
    client_ip = websocket.client.host

    # Configure limits
    rate_limit = await model.get_rate_per_minute() 
    print(f"Rate limit set: {rate_limit}", file=sys.stderr)
    rate_limit_period = 60
    poll_interval = 2
    receive_timeout = 30  # seconds

    try:
        while True:
            # Receive the message from the client with a timeout
            try:
                message = await asyncio.wait_for(
                    websocket.receive_text(), timeout=receive_timeout
                )
            except asyncio.TimeoutError:
                print("No message received within timeout.")
                continue  # Or you might want to close the connection
            except WebSocketDisconnect:
                print("WebSocket connection closed by client.")
                break
            
            print(f"received message: {message}")

            timestamp = datetime.now().isoformat()
            await chat_context.save_chat_message("user", message, timestamp=timestamp)
            print("calling process_response_recursively")
            async for event in process_response_recursively(
                websocket,
                rate_limit=rate_limit,
                period=rate_limit_period,
                poll_interval=poll_interval,
            ):
                # Send events through the WebSocket
                await websocket.send_json(event)
                print(f"sent event: {event}")

            await websocket.send_json({"type": "done"})
            print("done")

    except Exception as e:
        print(f"Error in WebSocket: {e}")
        traceback.print_exc()
        # Await sending of error messages
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
            await websocket.send_json({"type": "done"})
        except Exception as send_error:
            print(f"Error sending error message: {send_error}")
            traceback.print_exc()