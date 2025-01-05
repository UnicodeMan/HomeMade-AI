// scripts/script.js
import { SessionManager } from './sessionManager.js';
import { fetchSessionSummaries } from './sessionSummaries.js';
import { sendMessage } from './messageHandling.js';
import { escapeHtml, formatTimestamp } from './utils.js';
//import { setupWebSocket } from './webSocketHandler.js';
import { updateSessionInfo } from './uiUpdater.js';
import 'https://code.jquery.com/jquery-3.5.1.slim.min.js';
import 'https://cdn.jsdelivr.net/npm/@popperjs/core@2.9.2/dist/umd/popper.min.js';
import 'https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/js/bootstrap.min.js';

document.addEventListener('DOMContentLoaded', (event) => {
    // ... (Your DOMContentLoaded event handling logic) ...
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
    const currentModel = document.getElementById('currentModel');
    const changeModelButton = document.getElementById('changeModelButton');
    const modelSwitchModal = new bootstrap.Modal(document.getElementById('modelSwitchModal'));
    const providerSelect = document.getElementById('providerSelect');
    const modelSelect = document.getElementById('modelSelect');
    const confirmModelSwitchButton = document.getElementById('confirmModelSwitchButton');
    const modelSelectionContent = document.getElementById('modelSelectionContent');
    const loadingIndicator = document.getElementById('loadingIndicator');
    let allModels = [];

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const targetTabId = button.dataset.target;
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
    menuButton.addEventListener('click', () => {
        sideMenu.classList.toggle('open');
    });

    changeModelButton.addEventListener('click', async () => {
        // Indicate that list is loading
        modelSwitchModal.show();
        loadingIndicator.style.display = 'block';
        modelSelectionContent.style.display = 'none';

        // Fetch available providers and models
        const response = await fetch('/models/available-models');
        const data = await response.json();
        allModels = data.models.map(model => JSON.parse(model));
        
        const providers = [...new Set(allModels.map(model => model.provider))];
        providerSelect.innerHTML = providers.map(provider => `<option value="${provider}">${provider}</option>`).join('');

        // initialize selected provider models
        const selectedProvider = providerSelect.value;
        const models = allModels.filter(model => model.provider === selectedProvider);
        modelSelect.innerHTML = models.map(model => `<option value="${model.name}" data-description="${model.description}">${model.name}</option>`).join('');

        // Hide loading indicator and show model selection content
        loadingIndicator.style.display = 'none';
        modelSelectionContent.style.display = 'block';
    });

    providerSelect.addEventListener('change', () => {
        const selectedProvider = providerSelect.value;
        const models = allModels.filter(model => model.provider === selectedProvider);
        modelSelect.innerHTML = models.map(model => `<option value="${model.name}" data-description="${model.description}">${model.name}</option>`).join('');
    });

    modelSelect.addEventListener('mouseover', (event) => {
        if (event.target.tagName === 'OPTION') {
            const description = event.target.getAttribute('data-description');
            modelDescription.textContent = description;
        }
    });

    modelSelect.addEventListener('change', () => {
        const selectedOption = modelSelect.options[modelSelect.selectedIndex];
        const description = selectedOption.getAttribute('data-description');
        modelDescription.textContent = description;
    });

    confirmModelSwitchButton.addEventListener('click', async () => {
        const selectedProvider = providerSelect.value;
        const selectedModel = modelSelect.value;
        // Switch model
        const response = await fetch('/models/switch-model', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                model_name: selectedModel,
                provider: selectedProvider
            })
        }).then(res => res.json());

        if (response.status === 'success') {
            currentModel.textContent = selectedModel;
            modelSwitchModal.hide();
        } else {
            alert('Failed to switch model: ' + response.message);
        }
    });

    if (sessionManager.sessionManagerContainer) {
        sessionManager.sessionManagerContainer.innerHTML = sessionManager.render(); // Use innerHTML to set the HTML
    
      }
        // Auto-resize textarea
        userMessage.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 150) + 'px';
        });



    


    // Load chat history

    const outputUpdateIndicator = document.getElementById('outputUpdateIndicator');

    
    function showOutputUpdateIndicator() {
        outputUpdateIndicator.classList.add('visible');
        setTimeout(() => outputUpdateIndicator.classList.remove('visible'), 2000);
    }
    // send message to server when enter or button is pressed
    sendButton.disabled = false;

  // Event Listeners
  sendButton.addEventListener('click', sendMessage);

  userMessage.addEventListener('keypress', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          sendMessage();
      }
    });
// Initial fetch of session summaries
fetchSessionSummaries();
// Auto-resize textarea

});