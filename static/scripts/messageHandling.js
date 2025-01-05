// scripts/messageHandling.js
import { escapeHtml } from './utils.js';
import { formatTimestamp, formatTimestampForFrontend } from './utils.js';
export function addMessage(content, role, timestamp = undefined, isCommand = false) {
    console.log(content + "\n" + role)

    if(role === "command_output" || role === "command" || role === "assistant_response_command" || role === "ai_response_command" || isCommand) {
        addCommandOutput(content, role, formatTimestamp(formatTimestampForFrontend(timestamp)));
    }
    else {
        const messageDiv = document.createElement('div');

        messageDiv.className = `message ${role}-message`;
        
    
        messageDiv.innerHTML = `<pre class="wrap-text">${escapeHtml(content)}</pre>`; 
        const conversation = document.getElementById('conversation');

        conversation.appendChild(messageDiv);
   
        if (timestamp != undefined) {
            const timestampDiv = document.createElement('div');
            timestampDiv.className = 'timestamp';
            timestampDiv.textContent = formatTimestamp(formatTimestampForFrontend(timestamp));
            messageDiv.appendChild(timestampDiv);
        }
    }
    
}

export function addCommandOutput(content, role, timestamp) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `command-output ${role}`; 

    // Create icon element (you'll need to add the actual icons)
    const icon = document.createElement('span'); 
    icon.className = `command-output ${role}-icon`; // Add class for styling the icon
    messageDiv.appendChild(icon); // Add icon to the message div

    let formattedContent = String.raw`${content}`;
    formattedContent = escapeHtml(formattedContent).replace(/\\n/g, '<br>');

    const contentSpan = document.createElement('span'); // Wrap content in a span
    contentSpan.className = 'command-content'; 
    contentSpan.innerHTML = `<pre class="wrap-text">${formattedContent}</pre>`;
    messageDiv.appendChild(contentSpan); 
    const commandConversation = document.getElementById('commandConversation');

    if (timestamp != undefined) {
        const timestampDiv = document.createElement('div');
        timestampDiv.className = 'timestamp';
        timestampDiv.textContent = formatTimestamp(formatTimestampForFrontend(timestamp));
        messageDiv.appendChild(timestampDiv);
    }
    commandConversation.appendChild(messageDiv);
    commandConversation.scrollTop = commandConversation.scrollHeight;
    commandConversation.style.display = 'block';
}

export function sendMessage() {
    let userMessage = document.getElementById('userMessage');
    const message = userMessage.value.trim();
    if (!message) return;
    
    const socket = new WebSocket("ws://" + window.location.host + "/chat"); 
    const now = new Date();
    const options = { 
      timeZone: 'UTC', 
      hour12: true, // 12-hour format
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', second: '2-digit'
    };
    let utcString = now.toLocaleString('en-US', options);
    // Add user message to conversation
    addMessage(message, "user", utcString);
    // Clear input and show typing indicator
    userMessage.value = '';
    userMessage.style.height = 'auto';
    typing.style.display = 'block';
    typing.innerText = 'Typing...';

    socket.onopen = () => {
        console.log("WebSocket connection opened");
        socket.send(message); // Send the message when the connection is open
    };

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log("Received event:", data);

        switch (data.type) {
            case "ai_response":
                addMessage(data.response, "assistant", data.timestamp);
                //socket.close();
                typing.style.display = 'none';
                break;

            case "command_execution_start":
                typing.style.display = 'block';
                typing.innerText = 'Executing commands...';
                break;
            case "rate_limit":
                console.log("rate limit");
                typing.style.display = 'block';
                const initialRemainingSeconds = data.seconds;
                const endTime = Date.now() + initialRemainingSeconds * 1000;
    
                const intervalId = setInterval(() => {
                    const remainingSeconds = Math.max(0, Math.round((endTime - Date.now()) / 1000));
                    let previous_text = typing.innerText;
                    typing.innerText = `API limit reached. Waiting ${remainingSeconds}s.`;

                    if (remainingSeconds <= 0) {
                        clearInterval(intervalId);
                        typing.style.display = 'block';
                        typing.innerText = previous_text;

                    }
                }, 1000);
                break;
            case "command_output": // should be always this
                addCommandOutput(data.output, "system", data.timestamp);
                userMessage.value = '';
                userMessage.style.height = 'auto';
                typing.style.display = 'block';
                typing.innerText = 'Analyzing command output...';
            
                
                break;
            case "assistant_response_command":
                typing.style.display = 'none';
                addCommandOutput(data.response, "assistant", data.timestamp);
                userMessage.value = '';
                userMessage.style.height = 'auto';
                typing.style.display = 'block';
                typing.innerText = 'Typing...';
            
                
                break;
            case "ai_response_command": // this happens because backend sends this type of yield object, but in database it saves as assistant_response_command
                typing.style.display = 'none';
                addCommandOutput(data.response, "assistant", data.timestamp);
                userMessage.value = '';
                userMessage.style.height = 'auto';
                typing.style.display = 'block';
                typing.innerText = 'Typing...';
                
                    
                break;
            case "error":
                typing.style.display = 'none';
                addMessage(`Error: ${data.message}`, "backend");
                break;

            case "done":
                socket.close();
                typing.style.display = 'none';
                break;
        }
    };
    socket.onclose = () => {
        console.log("WebSocket connection closed");
    };

    socket.onerror = (error) => {
        console.error("WebSocket error:", error);
        typing.style.display = 'none';
        //addMessage("Error communicating with server", "system");
    };
}