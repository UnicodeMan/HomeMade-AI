 
// SessionManager class (no React needed)
let wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';

let wsUrl = `${wsProtocol}//${window.location.host}/ws`;  // Remove the hardcoded port

function escapeHtml(unsafe) {
    return unsafe
         .replace(/&/g, "&amp;")
         .replace(/</g, "&lt;")
         .replace(/>/g, "&gt;")
         .replace(/"/g, "&quot;")
         .replace(/'/g, "&#039;");
}

class SessionManager {
    constructor() {
        this.sessions = [];
        this.currentSession = null;
        this.sessionManagerContainer = document.getElementById('sessionManager'); 
        this.fetchSessions();
    }

    async fetchSessions() {
        try {
            const response = await fetch('/sessions/list');
            const data = await response.json();
            this.sessions = data.histories;
            this.currentSession = this.sessions[0]?.session_id || 'new'; // Set to first session ID or 'new'
            this.render();
            this.checkForNewConversations();
        } catch (error) {
            console.error('Error fetching sessions:', error);
        }
    }

    async checkForNewConversations() {
        const hasNewConversation = this.sessions.some(session => session.summary === "New conversation");
        if (hasNewConversation) {
            setTimeout(() => this.fetchSessions(), 5000); // Retry after 5 seconds
        }
    }

    handleSessionChange = async (value) => {
        try {
            const response = await fetch('/sessions/switch', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ session_id: value }),
            });
    
            if (!response.ok) throw new Error('Failed to switch session');
            
            const data = await response.json();
    
            // Update the current session
            this.currentSession = value;
            
            // Clear and update conversation display
            const conversation = document.getElementById('conversation');
            conversation.innerHTML = '';
            if (data.messages) {
                data.messages.forEach(msg => {
                    const messageDiv = document.createElement('div');
            
                    if (msg.role === "command_output") {
                        // Handle command output
                        let formattedContent = String.raw`${msg.content}`; // Maintain raw formatting
                        formattedContent = escapeHtml(formattedContent).replace(/\\n/g, '<br>'); // Replace literal \n with <br>
                        messageDiv.innerHTML = `<pre class="wrap-text">${formattedContent}</pre>`;
            
                        const commandConversation = document.getElementById('commandConversation');
                        commandConversation.appendChild(messageDiv);
                        commandConversation.scrollTop = commandConversation.scrollHeight;
                        commandConversation.style.display = 'block';
                        showOutputUpdateIndicator();
                    } else if (msg.role === "user" || msg.role === "assistant") {
                        // Handle user or assistant messages
                        messageDiv.className = `message ${msg.role}-message`;
                        messageDiv.innerHTML = `<pre class="wrap-text">${escapeHtml(msg.content)}</pre>`;
            
                        const conversation = document.getElementById('conversation');
                        conversation.appendChild(messageDiv);
            
                        if (msg.timestamp) {
                            const timestampDiv = document.createElement('div');
                            timestampDiv.className = 'timestamp';
                            timestampDiv.textContent = new Date(msg.timestamp).toLocaleTimeString();
                            messageDiv.appendChild(timestampDiv);
                        }
                    } else {
                        // Handle other or unknown roles (default case)
                        messageDiv.className = `message other-message`;
                        messageDiv.innerHTML = `<pre class="wrap-text">${escapeHtml(msg.content)}</pre>`;
            
                        const conversation = document.getElementById('conversation');
                        conversation.appendChild(messageDiv);
                    }
                });
            }
    
            // Update session info display
            const sessionInfo = document.getElementById('sessionInfo');
            sessionInfo.textContent = value === 'new' ? 'New Conversation' : `Session: ${value}`;
    
        } catch (error) {
            console.error('Error switching session:', error);
        }
    };

    formatTimestamp = (timestamp) => {
        return new Date(timestamp).toLocaleString();
    };
      
    render() {
        if (!this.sessionManagerContainer) return;

        const selectHtml = `
            <select id="sessionSelect" value="${this.currentSession || ''}">
                <option value="new">Start a new conversation</option>
                ${this.sessions.map(session => `
                    <option key="${session.session_id}" value="${session.session_id}">
                        ${session.summary}
                    </option>
                `).join('')}
            </select>
        `;
    
        this.sessionManagerContainer.innerHTML = selectHtml;
    
        // Attach the onchange event using JavaScript
        const sessionSelect = document.getElementById('sessionSelect');
        sessionSelect.addEventListener('change', (event) => {
            this.handleSessionChange(event.target.value);
        });
    }
}

document.addEventListener('DOMContentLoaded', (event) => {
    // DOM Elements
    const conversation = document.getElementById('conversation');
    const userMessage = document.getElementById('userMessage');
    const sendButton = document.getElementById('sendButton');
    const typing = document.getElementById('typing');
    const commandWindow = document.getElementById('commandWindow');
    const commandHeader = document.getElementById('commandHeader');
    const commandConversation = document.getElementById('commandConversation');
    const minimizeButton = document.getElementById('minimizeButton');
    const sessionManager = new SessionManager()
    const menuButton = document.getElementById('menuButton');
    const sideMenu = document.getElementById('sideMenu');
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');
  
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const targetTabId = button.dataset.target;
            // ... (Hide all tab contents, show the target tab, and update active button styling)
            tabContents.forEach(content => {
                content.classList.remove('active');
            });
        
            tabButtons.forEach(btn => {
                btn.classList.remove('active');
            });
        
            document.getElementById(targetTabId).classList.add('active');
            button.classList.add('active');
        });
    });
    // Side menu toggle
    menuButton.addEventListener('click', () => {
        sideMenu.classList.toggle('open');
    });
    // WebSocket connection
    console.log("Attempting to connect to WebSocket at:", wsUrl);
    const sessionManagerContainer = document.getElementById('sessionManager');


    // Initialize session info display
    const sessionInfo = document.getElementById('sessionInfo');
    if (sessionInfo) {
        sessionInfo.textContent = 'New Conversation';
    }
    let isDragging = false;
    let offsetX = 0;
    let offsetY = 0;

    // Message handling functions
    function formatTimestamp(isoString) {
        const date = new Date(isoString);
        return date.toLocaleTimeString();
    }

    function addMessage(content, role, timestamp = null, isCommand = false) {
        console.log(content + "\n" + role)

        if(role === "command_output") {
            const messageDiv = document.createElement('div');

            let formattedContent = String.raw`${content}`; //This is crucial
            formattedContent = escapeHtml(formattedContent).replace(/\\n/g, '<br>'); // Replace literal \ followed by n
            messageDiv.innerHTML = `<pre class="wrap-text">${formattedContent}</pre>`;
            const commandConversation = document.getElementById('commandConversation');
            commandConversation.appendChild(messageDiv);
            commandConversation.scrollTop = commandConversation.scrollHeight;
            commandConversation.style.display = 'block';
            showOutputUpdateIndicator();

        }
        else if(isCommand == false) {
            const messageDiv = document.createElement('div');

            messageDiv.className = `message ${role}-message`;
            
        
            messageDiv.innerHTML = `<pre class="wrap-text">${escapeHtml(content)}</pre>`; 
            const conversation = document.getElementById('conversation');
 
            conversation.appendChild(messageDiv);
       
            if (timestamp) {
                const timestampDiv = document.createElement('div');
                timestampDiv.className = 'timestamp';
                timestampDiv.textContent = formatTimestamp(timestamp);
                messageDiv.appendChild(timestampDiv);
            }
        }
        else if (isCommand) {
            commandConversation.appendChild(messageDiv);
            commandConversation.style.display = 'block';
            commandConversation.scrollTop = commandConversation.scrollHeight;
            showOutputUpdateIndicator();
        } else {
            const messageDiv = document.createElement('div');

            conversation.appendChild(messageDiv);
            conversation.scrollTop = conversation.scrollHeight;
        }
    }
    
    function addCommandOutput(content) {
        const messageDiv = document.createElement('div');
        let formattedContent = String.raw`${content}`; // Maintain raw formatting
        formattedContent = escapeHtml(formattedContent).replace(/\\n/g, '<br>');
        messageDiv.innerHTML = `<pre class="wrap-text">${formattedContent}</pre>`;
    
        const commandConversation = document.getElementById('commandConversation');
        commandConversation.appendChild(messageDiv);
    
        // Scroll to bottom if not minimized
        if (commandConversation.classList.contains('maximized')) {
            commandConversation.scrollTop = commandConversation.scrollHeight;
            commandConversation.style.display = 'block';
        }
        // Show update indicator if minimized
        if (commandConversation.classList.contains('minimized')) {
            showOutputUpdateIndicator();
            commandConversation.style.display = 'none';
        }
    }
    

  if (sessionManagerContainer) {
    sessionManagerContainer.innerHTML = sessionManager.render(); // Use innerHTML to set the HTML

  }
    // Auto-resize textarea
    userMessage.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 150) + 'px';
    });
    let resizing = false;
    let startX, startY;
    
    const resizer = document.createElement('div'); // Add a resizer element
    resizer.style.cssText = 'position: absolute; bottom: 0; right: 0; width: 10px; height: 10px; background-color: #374151; cursor: se-resize;';
    //commandConversation.appendChild(resizer);
    console.log("Full js execution completed!");
    commandConversation.addEventListener('mousedown', (e) => {
        resizing = true;
        startX = e.clientX;
        startY = e.clientY;
    });

    document.addEventListener('mousemove', (e) => {
        if (resizing) {
            const width = Math.min(800, Math.max(300, e.clientX - commandConversation.offsetLeft));
            const height = Math.min(600, Math.max(200, e.clientY - commandConversation.offsetTop));
            commandConversation.style.width = width + 'px';
            commandConversation.style.height = height + 'px';
        }
    });
   
    console.log("Full js execution completed!");

    document.addEventListener('mouseup', () => {
        resizing = false;
    });
    console.log("Full js execution completed!");
    console.log("Full js execution completed!");
    console.log("Full js execution completed!");
    console.log("Full js execution completed!");
    // Command window drag functionality
    resizer.addEventListener('mousedown', (e) => {
        resizing = true;
        e.stopPropagation(); // Prevent drag conflicts
        startX = e.clientX;
        startY = e.clientY;
    });


    document.addEventListener('mousemove', (e) => {
        if (isDragging) {
            commandConversation.style.left = `${e.clientX - offsetX}px`;
            commandConversation.style.top = `${e.clientY - offsetY}px`;
        }
    });
    console.log("Full js execution completed!");

    document.addEventListener('mouseup', () => {
        isDragging = false;
        commandConversation.style.transition = "";
    });


    // Load chat history

    const outputUpdateIndicator = document.getElementById('outputUpdateIndicator');
/*
    let commandWindowState = 'minimized'; // or 'minimized'
    commandConversation.classList.add('minimized');
    commandConversation.classList.remove('maximized');
*/
/*
minimizeButton.addEventListener('click', () => {
    if (commandWindowState === 'minimized') {
        commandWindowState = 'maximized';
        commandConversation.classList.remove('minimized');
        commandConversation.classList.add('maximized');
        commandConversation.style.height = '30vh';

        commandConversation.style.display = 'block';
        minimizeButton.textContent = '_';
    } else {
        commandWindowState = 'minimized';
        commandConversation.classList.add('minimized');
        commandConversation.classList.remove('maximized');
        minimizeButton.textContent = '▢';
        commandConversation.style.height = '0vh';

    }
});
*/
    
    function showOutputUpdateIndicator() {
        outputUpdateIndicator.classList.add('visible');
        setTimeout(() => outputUpdateIndicator.classList.remove('visible'), 2000);
    }

// Update the existing addCommandOutput function
function addCommandOutput(content) {
    const messageDiv = document.createElement('div');
    let formattedContent = String.raw`${content}`; //Maintain raw formatting
    formattedContent = escapeHtml(formattedContent).replace(/\\n/g, '<br>');
    messageDiv.innerHTML = `<pre class="wrap-text">${formattedContent}</pre>`;
    
    const commandConversation = document.getElementById('commandConversation');
    commandConversation.appendChild(messageDiv);
    commandConversation.scrollTop = commandConversation.scrollHeight;
    commandConversation.style.display = 'block';
    
    // Show the command window if it's minimized
    if (commandConversation.classList.contains('minimized')) {
        showOutputUpdateIndicator();
    }
}
  // Enable send button immediately since we're not waiting for WebSocket connection
  sendButton.disabled = false;

  // Event Listeners
  sendButton.addEventListener('click', sendMessage);

  userMessage.addEventListener('keypress', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          sendMessage();
      }
  });
  // Function to fetch session summaries
  async function fetchSessionSummaries() {
    try {
        const response = await fetch('/sessions/list');
        const data = await response.json();
        const summaries = data.histories;

        // Clear existing options except the first one
        while (sessionSelect.options.length > 1) {
            sessionSelect.remove(1);
        }

        // Add new options
        summaries.forEach(summary => {
            const option = document.createElement('option');
            option.value = summary.session_id;
            option.text = summary.summary;
            sessionSelect.appendChild(option);
        });

        // Check if any summary is still "New conversation" and refetch if necessary
        const hasNewConversation = summaries.some(summary => summary.summary === "New conversation");
        if (hasNewConversation) {
            setTimeout(fetchSessionSummaries, 5000); // Retry after 5 seconds
        }
    } catch (error) {
        console.error('Error fetching session summaries:', error);
    }
}

// Initial fetch of session summaries
fetchSessionSummaries();
  // Auto-resize textarea
  userMessage.addEventListener('input', function() {
      this.style.height = 'auto';
      this.style.height = Math.min(this.scrollHeight, 150) + 'px';
  });
    // Show the indicator when new output is added

});

