```python
import base64
import json
import requests

def send_file_to_gemini(file_path, mime_type, api_key, model_name="gemini-pro-vision"):
    """
    Sends a file to the Gemini API's generateContent endpoint.

    Args:
        file_path (str): The path to the file.
        mime_type (str): The MIME type of the file (e.g., "image/jpeg", "audio/mpeg", "text/plain").
        api_key (str): Your Google AI API key.
        model_name (str): The name of the Gemini model to use (defaults to "gemini-pro-vision").

    Returns:
        dict: The JSON response from the Gemini API, or None if there's an error.
    """
    try:
        with open(file_path, "rb") as f:
            file_content = f.read()
        
        base64_encoded_content = base64.b64encode(file_content).decode()

        request_body = {
            "contents": [
                {
                    "parts": [
                        {
                            "inlineData": {
                                "mimeType": mime_type,
                                "data": base64_encoded_content
                            }
                        }
                    ]
                }
            ]
        }

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        headers = {'Content-Type': 'application/json'}

        response = requests.post(url, headers=headers, json=request_body)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json()

    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error during API request: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None


if __name__ == "__main__":
    # Replace with your actual file path, MIME type, and API key
    file_path = "dummy.txt"
    mime_type = "text/plain"
    api_key = "YOUR_API_KEY"

    # Create a dummy file for the example
    with open(file_path, "w") as f:
        f.write("This is a dummy text file for testing.")


    response = send_file_to_gemini(file_path, mime_type, api_key)
    
    if response:
        print("Gemini API Response:")
        print(json.dumps(response, indent=2))
    else:
        print("Failed to send file to Gemini API.")

```

**Explanation:**

1.  **`send_file_to_gemini(file_path, mime_type, api_key, model_name)` function:**
    *   Takes the `file_path`, `mime_type`, and `api_key` as input. You'll need to replace `"YOUR_API_KEY"` with your actual Gemini API key.
    *   Reads the file content in binary mode (`"rb"`).
    *   Base64 encodes the file content.
    *   Constructs the JSON request body with the `mimeType` and the base64-encoded data in the `inlineData` field.
    *   Sends the request to the Gemini API's `generateContent` endpoint using the `requests.post` method.
    *   Handles potential errors such as file not found, API request failures, and other exceptions.
    *   Returns the JSON response if successful or `None` if there's an error.
2.  **`if __name__ == "__main__":` block:**
    *   This block demonstrates how to use the `send_file_to_gemini` function.
    *   It sets example values for `file_path`, `mime_type` and `api_key`.
    *   It then calls the `send_file_to_gemini` and prints the API response.
    *   **Important:** Replace `"YOUR_API_KEY"` with your actual API key and create your test file at `dummy.txt`.

**To use this code:**

1.  **Replace `"YOUR_API_KEY"` with your actual Gemini API key.**
2.  **Create a file named `dummy.txt`** (or change the `file_path` variable) and put some data into it.
3.  **Run the python code.**