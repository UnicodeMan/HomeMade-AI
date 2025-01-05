import { escapeHtml } from './utils.js';
import { addMessage, addCommandOutput } from './messageHandling.js';
export class SessionManager {

    constructor() {
        this.sessions = [];
        this.currentSession = null;
        this.sessionManagerContainer = document.getElementById('sessionManager'); 
        this.fetchSessions();
    }
    formatTimestamp(timestamp) {
        return new Date(timestamp).toLocaleString();
    }
    async fetchSessions() {
        try {
            const response = await fetch('/sessions/list');
            const data = await response.json();
            this.sessions = data.histories;
            this.render();
        } catch (error) {
            console.error('Error fetching sessions:', error);
        }
    }

    async checkForNewConversations() {
        const hasNewConversation = this.sessions.some(session => session.summary === "New conversation");
        if (hasNewConversation) {
            setTimeout(() => this.fetchSessions(), 5000);
        }
    }
    
   
    async handleSessionChange(value) {
        try {
            const typing = document.getElementById('typing');
            typing.style.display = 'block';
            typing.innerText = 'Loading session...';
        
            const response = await fetch('/sessions/switch', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ session_id: value }),
            });
            
            if (!response.ok) {
                throw new Error('Failed to switch session');
            }

            this.currentSession = value;

            const data = await response.json();
            const conversation = document.getElementById('conversation');
            conversation.innerHTML = '';

            if (data.messages) {
                data.messages.forEach(msg => {
                    console.log(msg)
                    if(msg.timestamp == undefined) {
                        addMessage(msg.content, msg.role);
                    }
                    else {
                        addMessage(msg.content, msg.role, msg.timestamp);
                    }
                });
            }

            // Update session info display
            const sessionInfo = document.getElementById('sessionInfo');
            if (sessionInfo) {
                const session = this.sessions.find(s => s.session_id === value);
                const displayText = value === 'new' ? 'New Conversation' : 
                    (session ? `${session.summary}` : `Session ${value}`);
                sessionInfo.textContent = displayText;
            }
            typing.style.display = 'none';
        } catch (error) {
            console.error('Error switching session:', error);
            alert(`Failed to switch session: ${error.message}`);
            typing.style.display = 'hidden';

        }
    }

    render() {
        if (!this.sessionManagerContainer) return;

        const selectHtml = `
            <select id="sessionSelect">
                <option value="new" ${this.currentSession === 'new' ? 'selected' : ''}>Start a new conversation</option>
                ${this.sessions.map(session => {
                    const timeString = this.formatTimestamp(session.timestamp);
                    const displayText = session.summary === "New conversation" 
                        ? `${timeString} - New conversation`
                        : `${timeString} - ${session.summary}`;
                    
                    return `
                        <option value="${session.session_id}" ${this.currentSession === session.session_id ? 'selected' : ''}>
                            ${displayText}
                        </option>
                    `;
                }).join('')}
            </select>
        `;

        this.sessionManagerContainer.innerHTML = selectHtml;

        const sessionSelect = document.getElementById('sessionSelect');
        sessionSelect.addEventListener('change', (event) => {
            this.handleSessionChange(event.target.value);
        });
    }

}