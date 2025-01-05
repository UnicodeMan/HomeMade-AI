import os
from typing import List
from datetime import datetime

def drop_privileges(uid, gid):
    def _drop():
        os.setgid(gid)
        os.setuid(uid)
        os.chdir("/home/ai")  # Change working directory
        os.environ['HOME'] = "/home/ai"

    return _drop

def detect_unterminated_tags(response: str) -> List[str]:
    """
    Detects unterminated tags in the response.
    Args:
        response (str): The AI response to check.

    Returns:
        List[str]: A list of unterminated tags (e.g., ["[PYTHON]", "[EXECUTE]"]).
    """
    tags = ["[PYTHON]", "[EXECUTE]"]
    unterminated = []

    for tag in tags:
        if tag in response and response.count(tag) > response.count(tag.replace("[", "[/")):
            unterminated.append(tag)

    return unterminated

def format_timestamp_for_frontend(backend_timestamp):
  """
  Converts a backend timestamp (ISO 8601 format) to the format expected by the frontend.

  Args:
    backend_timestamp: A timestamp string in ISO 8601 format (e.g., "2025-01-05T15:12:17.658007").

  Returns:
    A timestamp string in the format "MM/DD/YYYY, HH:MM:SS AM/PM" (e.g., "01/05/2025, 03:12:17 PM").
  """
  # Parse the backend timestamp
  dt_object = datetime.strptime(backend_timestamp, "%Y-%m-%dT%H:%M:%S.%f")

  # Format the timestamp for the frontend
  frontend_timestamp = dt_object.strftime("%m/%d/%Y, %I:%M:%S %p") 
  return frontend_timestamp

