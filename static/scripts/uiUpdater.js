// scripts/uiUpdater.js
export function updateSessionInfo(sessionId) {
    const sessionInfo = document.getElementById('sessionInfo');
    sessionInfo.textContent = sessionId === 'new' ? 'New Conversation' : `Session: ${sessionId}`;
}

// ... (Other UI update functions) ...