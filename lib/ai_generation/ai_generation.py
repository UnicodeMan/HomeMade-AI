from ..shell_environment import ShellEnvironment
from typing import Optional, List, Dict
import asyncio
import google.generativeai as genai
from ..models import *
from asyncio import Semaphore
from ..chat_history import ChatContext
from fastapi import FastAPI
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi import Request
from ..limiter import RateLimiter
from ..utils import format_timestamp_for_frontend, detect_unterminated_tags
import json
import traceback
from fastapi import WebSocket
import sys
import os
from datetime import datetime
async def process_response_recursively(
    websocket: WebSocket,
    input_text: str = None,
    iteration: int = 1,
    max_iterations: int = 50,
    rate_limit: int = 2,
    period: int = 60,
    poll_interval: int = 5,
    session_id = None,
):
    """
    Process the response recursively with rate limiting and concurrency control.
    Ensures AI responses and command outputs are yielded as separate events.
    """
    print("in process_response_recursively")
    try:
        chat_context: ChatContext = websocket.app.state.chat_context
        conversation = await chat_context.get_conversation()
        model = websocket.app.state.model
        model_name = await model.get_model_name()
        provider = await model.get_provider()
        print(f"Model name: {model_name}\nProvider: {provider}", file=sys.stderr)
        if session_id and await chat_context.session_exists(session_id):
            await chat_context.load_session(session_id) #load session if provided
        else:
            await chat_context.new_conversation()


        if iteration > max_iterations:
            yield {
                "type": "error",
                "message": "Maximum recursion limit reached."
            }
            return

        print(f"Processing iteration: {iteration}")
    
        rate_limiter: RateLimiter = websocket.app.state.rate_limiter
        client_ip = websocket.client.host
        is_limited, remaining_time = await rate_limiter.check_and_update_limit(
            f"{client_ip}:recursive_call",
            limit=rate_limit,
            period=period
        )
    
        if is_limited:
            yield {
                'type': 'rate_limit',
                'seconds': remaining_time
            }
            print(f"API limit reached. Waiting {remaining_time} seconds")
            # Wait for the rate limit to expire
            await rate_limiter.enforce_limit(
                f"{client_ip}:recursive_call", 
                rate_limit, 
                period, 
                poll_interval=poll_interval
            )
        # Generate AI response
        timestamp = None
        response = None  # Initialize the response variable
        if(conversation[-1]["role"] == "command" and input_text != None):
            conversation.pop()
            conversation.pop()
            conversation.append({"role": "command", "content": input_text, "timestamp": datetime.now().isoformat()})
        try:
            # Run the synchronous generate_content in a thread pool
            print("calling generate_content")
            response = await model.generate_content(
                    conversation,
                    temperature=0.89
                )

        except Exception as e:
            print(f"Error generating content: {str(e)}")
            traceback.print_exc()
            yield {
                "type": "error",
                "message": f"Error generating content: {str(e)}"
            }
            return
     
        if(response.type == ModelResponseType.ERROR):
            error_message = response.error.lower()
            traceback.print_exc()
            if "copyright" in error_message:
                print("AI response contained copyrighted material. Re-prompting AI.")
                await chat_context.save_chat_message("system", "AI response contained copyrighted material. Re-prompting AI.", timestamp=datetime.now().isoformat())
                async for message in process_response_recursively(
                    websocket,
                    session_id=session_id,
                    iteration=iteration + 1,
                    max_iterations=max_iterations,
                    rate_limit=rate_limit,
                    period=period,
                    poll_interval=poll_interval
                ):
                    yield message
                return
            elif "token limit" in error_message or "too long" in error_message:
                print("Token limit exceeded. Trimming chat history and re-prompting AI.")
                await chat_context.save_chat_message("system", "Token limit exceeded. Trimming chat history and re-prompting AI.", timestamp=datetime.now().isoformat())
                await chat_context._trim_chat_history()

                async for message in process_response_recursively(
                    websocket,
                    session_id=session_id,
                    iteration=iteration + 1,
                    max_iterations=max_iterations,
                    rate_limit=rate_limit,
                    period=period,
                    poll_interval=poll_interval
                ):
                    yield message
                return
            else:
                yield {
                    "type": "error",
                    "message": f"An error occurred: {error_message}"
                }
                return
        ai_response = response.content
        print(f"AI response: {ai_response}", file=sys.stderr)
        unterminated_tags = detect_unterminated_tags(ai_response)
        # Extract and process commands if present
        commands = await websocket.app.state.shell_env.extract_commands(ai_response)

        if any(commands.values()) and len(unterminated_tags) == 0:
                # Indicate command execution start
            yield {
                "type": "command_execution_start",
                    "iteration": iteration
            }
            # Always yield AI response as a separate event
            yield {
                "type": "ai_response_command",
                "response": ai_response,
                "iteration": iteration,
                "timestamp": timestamp
            }
            await chat_context.save_chat_message("assistant_response_command", ai_response, timestamp=datetime.now().isoformat())
            # Execute commands and yield output as separate event
            command_output = await websocket.app.state.shell_env.execute_commands(commands)
            yield {
                "type": "command_output",
                "output": command_output,
                "iteration": iteration,
                "timestamp": timestamp
            }
            await chat_context.save_chat_message("command", command_output, datetime.now().isoformat()) 
            #save command output as message

            # Prepare context for next iteration
            new_input_text = (
               # f"{chat_context.system_prompt}\n"
                f"A reminder from user:"
                f"For bash commands, use: [EXECUTE]command[/EXECUTE]"
                f"For Python code, use: [PYTHON]code[/PYTHON]" 
                f"When you're finished, respond without executing anything"
                f"Assistant: {ai_response}\n" # Include the AI's response from the current iteration
                f"Commands executed: {commands}\n"
                f"Command output: {command_output}" 
            )
            #{"role": "system", "content": new_input_text, "timestamp": "None"})
            # Process next iteration, but *don't* yield from this call
            async for event in process_response_recursively(
                websocket,
                input_text=new_input_text,
                iteration = iteration + 1,
                max_iterations=max_iterations,
                rate_limit=rate_limit,
                period=period,
                poll_interval=poll_interval,
                session_id=chat_context.session_id #propagate session id for next iterations
            ):
                yield event
        elif len(unterminated_tags) > 0:
            yield {
                "type": "error",
                "message": f"Unmatched tags found in AI response: {unterminated_tags}"
            }
            chat_context.save_chat_message("system", f"Unmatched tags found in AI response: {unterminated_tags}", timestamp=datetime.now().isoformat())
            new_input_text = f"Your response contained unmatched tags. Please try again."
            async for event in process_response_recursively(
                websocket,
                input_text=new_input_text,
                session_id=session_id,
                iteration=iteration + 1,
                max_iterations=max_iterations,
                rate_limit=rate_limit,
                period=period,
                poll_interval=poll_interval
            ):
                yield event
        else:
            # Save response if no commands to execute
            timestamp = datetime.now().isoformat()
            await chat_context.save_chat_message("assistant", ai_response, datetime.now().isoformat())
            yield {
                "type": "ai_response",
                "response": ai_response,
                "iteration": iteration,
                "timestamp": timestamp
            }


    except Exception as e:
        print(f"Error during iteration {iteration}: {str(e)}")
        traceback.print_exc()
        yield {
            "type": "error",
            "message": f"Error during iteration {iteration}: {str(e)}"
        }
    finally:
        #chat_context.save_history_to_db() # save the conversation to db on each iteration
        pass
async def generate_content_with_limit(
    model,
    input_text,
    semaphore: Optional[asyncio.Semaphore] = None,
    temperature: float = 1.0,
    client_id: str = None
):    
    """
    Async rate-limited wrapper for the model.generate_content method.
    """
    print("generating content")
    async with semaphore:
        try:
            conversation = list([{"role": "system_prompt", "content": input_text, "timestamp": datetime.now().isoformat()}])
            content = await model.generate_content(conversation, temperature=temperature)
            #print(f"generated content: {content}")
        finally:
            pass
    return content

