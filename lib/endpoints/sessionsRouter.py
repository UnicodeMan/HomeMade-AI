import os
import google.generativeai as genai
from lib.models import models
from lib.utils import utils
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi import Query
from fastapi import APIRouter, Request
from ..chat_history import ChatContext
import asyncio
from asyncio import Semaphore
from ..utils import detect_unterminated_tags
import json
from ..ai_generation import process_response_recursively
from datetime import datetime
from fastapi import Depends, Request
import redis
from fastapi import HTTPException
import redis
import sqlite3
import traceback


sessionRouter = APIRouter()


@sessionRouter.get("/sessions/list")
async def list_sessions(request: Request):
    try:
        chat_context: ChatContext = request.app.state.chat_context
        summaries = await chat_context.list_sessions()
        return {"histories": summaries}
    except Exception as e:
        print("Exception occurred in /sessions/list endpoint:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    
@sessionRouter.post("/sessions/switch")
async def switch_session(request: Request, session_data: dict):
    try:
        session_id = session_data.get("session_id")
        print("requested session id: ", session_id)
        chat_context: ChatContext = request.app.state.chat_context
        
        if session_id == "new":
            # Create new session
            await chat_context.new_conversation()
            return {"messages": []}
        if not await chat_context.session_exists(session_id):
            raise HTTPException(status_code=404, detail="Session not found")

        # Load existing session from the database
        history = await chat_context.load_session(session_id=session_id)
        
        return history
        
    except HTTPException:
        traceback.print_exc()
        raise
    except Exception as e:
        print("Exception occurred in switch_session:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
@sessionRouter.get("/sessions/summary")
async def get_session_summary(request: Request):
    try:
        chat_context: ChatContext = request.app.state.chat_context
        summary = chat_context.get_summary()
        return {"summary": summary}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
@sessionRouter.get("/sessions/current")
async def get_current_session(request: Request):
    """
    Endpoint to retrieve the current session ID.
    """
    try:
        chat_context: ChatContext = request.app.state.chat_context 
        current_session_id = chat_context.session_id
        return {"session_id": current_session_id}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error retrieving session ID: {e}")