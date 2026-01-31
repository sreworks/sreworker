// AI Code Worker Manager - Frontend Application

class WorkerManagerApp {
    constructor() {
        this.apiBase = window.location.origin;
        this.currentWorkerId = null;
        this.websocket = null;
        this.workers = [];

        this.initializeElements();
        this.attachEventListeners();
        this.loadWorkers();
    }

    initializeElements() {
        // Buttons
        this.newWorkerBtn = document.getElementById('new-worker-btn');
        this.sendBtn = document.getElementById('send-btn');
        this.deleteWorkerBtn = document.getElementById('delete-worker-btn');

        // Containers
        this.workersList = document.getElementById('workers-list');
        this.messagesContainer = document.getElementById('messages-container');
        this.messageInput = document.getElementById('message-input');

        // Panels
        this.noWorkerSelected = document.getElementById('no-worker-selected');
        this.chatInterface = document.getElementById('chat-interface');

        // Worker info
        this.currentWorkerName = document.getElementById('current-worker-name');
        this.currentWorkerAiCli = document.getElementById('current-worker-ai-cli');
        this.currentWorkerStatus = document.getElementById('current-worker-status');

        // Modal
        this.modal = document.getElementById('create-worker-modal');
        this.createWorkerForm = document.getElementById('create-worker-form');
    }

    attachEventListeners() {
        // New Worker button
        this.newWorkerBtn.addEventListener('click', () => this.showCreateWorkerModal());

        // Send message
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        this.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Delete worker
        this.deleteWorkerBtn.addEventListener('click', () => this.deleteCurrentWorker());

        // Modal close buttons
        document.querySelectorAll('.modal-close, .modal-cancel').forEach(btn => {
            btn.addEventListener('click', () => this.hideModal());
        });

        // Create worker form
        this.createWorkerForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.createWorker();
        });

        // Close modal on background click
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.hideModal();
            }
        });
    }

    async loadWorkers() {
        try {
            const response = await fetch(`${this.apiBase}/api/workers`);
            const data = await response.json();

            this.workers = data.workers || [];
            this.renderWorkersList();
        } catch (error) {
            console.error('Failed to load workers:', error);
            this.showError('Failed to load workers');
        }
    }

    renderWorkersList() {
        if (this.workers.length === 0) {
            this.workersList.innerHTML = '<p class="empty-state">No workers yet. Create one to get started!</p>';
            return;
        }

        this.workersList.innerHTML = this.workers.map(worker => `
            <div class="worker-item ${worker.id === this.currentWorkerId ? 'active' : ''}"
                 data-worker-id="${worker.id}">
                <div class="worker-item-header">
                    <strong>${worker.name}</strong>
                    <span class="ai-cli-badge">${worker.ai_cli_type}</span>
                </div>
                <div class="worker-item-meta">
                    <span class="status-badge status-${worker.status}">${worker.status}</span>
                    <span class="worker-path">${this.truncatePath(worker.project_path)}</span>
                </div>
            </div>
        `).join('');

        // Attach click handlers
        document.querySelectorAll('.worker-item').forEach(item => {
            item.addEventListener('click', () => {
                const workerId = item.dataset.workerId;
                this.selectWorker(workerId);
            });
        });
    }

    truncatePath(path, maxLength = 40) {
        if (path.length <= maxLength) return path;
        return '...' + path.slice(-(maxLength - 3));
    }

    async selectWorker(workerId) {
        this.currentWorkerId = workerId;
        const worker = this.workers.find(w => w.id === workerId);

        if (!worker) return;

        // Update UI
        this.noWorkerSelected.style.display = 'none';
        this.chatInterface.style.display = 'flex';

        this.currentWorkerName.textContent = worker.name;
        this.currentWorkerAiCli.textContent = worker.ai_cli_type;
        this.currentWorkerStatus.textContent = worker.status;
        this.currentWorkerStatus.className = `status-badge status-${worker.status}`;

        // Update worker list
        this.renderWorkersList();

        // Clear messages
        this.messagesContainer.innerHTML = '';

        // Connect WebSocket
        this.connectWebSocket(workerId);
    }

    connectWebSocket(workerId) {
        // Close existing WebSocket
        if (this.websocket) {
            this.websocket.close();
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/${workerId}`;

        this.websocket = new WebSocket(wsUrl);

        this.websocket.onopen = () => {
            console.log('WebSocket connected');
            this.addSystemMessage('Connected to worker');
        };

        this.websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
        };

        this.websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.addSystemMessage('WebSocket connection error', 'error');
        };

        this.websocket.onclose = () => {
            console.log('WebSocket closed');
            this.addSystemMessage('Disconnected from worker');
        };
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'connected':
                this.addSystemMessage(`Connected to ${data.worker_name} (${data.ai_cli_type})`);
                break;

            case 'history':
                if (data.messages && data.messages.length > 0) {
                    data.messages.forEach(msg => this.addMessage(msg));
                }
                break;

            case 'output':
                this.addMessage(data.content);
                break;

            case 'error':
                this.addSystemMessage(data.content, 'error');
                break;

            case 'pong':
                // Heartbeat response
                break;

            default:
                console.log('Unknown message type:', data.type);
        }
    }

    addMessage(messageData) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message message-${messageData.type || 'assistant'}`;

        const content = typeof messageData.content === 'string'
            ? messageData.content
            : JSON.stringify(messageData.content, null, 2);

        messageDiv.innerHTML = `
            <div class="message-header">
                <span class="message-role">${messageData.type || messageData.role || 'assistant'}</span>
                <span class="message-time">${this.formatTime(messageData.timestamp)}</span>
            </div>
            <div class="message-content">${this.escapeHtml(content)}</div>
        `;

        this.messagesContainer.appendChild(messageDiv);
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    addSystemMessage(content, type = 'info') {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message message-system message-${type}`;
        messageDiv.innerHTML = `
            <div class="message-content">${this.escapeHtml(content)}</div>
        `;

        this.messagesContainer.appendChild(messageDiv);
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    sendMessage() {
        const message = this.messageInput.value.trim();

        if (!message || !this.websocket) return;

        // Send via WebSocket
        this.websocket.send(JSON.stringify({
            type: 'message',
            content: message
        }));

        // Add to UI
        this.addMessage({
            type: 'user',
            content: message,
            timestamp: new Date().toISOString()
        });

        // Clear input
        this.messageInput.value = '';
        this.messageInput.focus();
    }

    showCreateWorkerModal() {
        this.modal.style.display = 'flex';
        document.getElementById('worker-name').focus();
    }

    hideModal() {
        this.modal.style.display = 'none';
        this.createWorkerForm.reset();
    }

    async createWorker() {
        const formData = new FormData(this.createWorkerForm);
        const data = {
            name: formData.get('name'),
            project_path: formData.get('project_path'),
            ai_cli_type: formData.get('ai_cli_type')
        };

        try {
            const response = await fetch(`${this.apiBase}/api/workers`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to create worker');
            }

            const worker = await response.json();

            this.hideModal();
            await this.loadWorkers();
            this.selectWorker(worker.id);

            this.showSuccess('Worker created successfully');
        } catch (error) {
            console.error('Failed to create worker:', error);
            this.showError(error.message);
        }
    }

    async deleteCurrentWorker() {
        if (!this.currentWorkerId) return;

        if (!confirm('Are you sure you want to delete this worker?')) return;

        try {
            const response = await fetch(`${this.apiBase}/api/workers/${this.currentWorkerId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error('Failed to delete worker');
            }

            // Close WebSocket
            if (this.websocket) {
                this.websocket.close();
                this.websocket = null;
            }

            // Reset UI
            this.currentWorkerId = null;
            this.noWorkerSelected.style.display = 'flex';
            this.chatInterface.style.display = 'none';

            await this.loadWorkers();

            this.showSuccess('Worker deleted successfully');
        } catch (error) {
            console.error('Failed to delete worker:', error);
            this.showError('Failed to delete worker');
        }
    }

    formatTime(timestamp) {
        if (!timestamp) return '';

        const date = new Date(timestamp);
        return date.toLocaleTimeString();
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showSuccess(message) {
        alert(message); // Simple alert for now, can be replaced with toast notification
    }

    showError(message) {
        alert('Error: ' + message); // Simple alert for now, can be replaced with toast notification
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new WorkerManagerApp();
});
