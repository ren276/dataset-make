// research_ui/js/app.js
// Configurable API Base URL (default relative path for localhost API)
const API_BASE_URL = window.location.origin.includes('http') ? window.location.origin : 'http://localhost:8000';

let chatHistory = [];

document.addEventListener('DOMContentLoaded', () => {
    checkServiceHealth();
    setupInputListeners();
});

async function checkServiceHealth() {
    const badge = document.getElementById('statusBadge');
    try {
        const res = await fetch(`${API_BASE_URL}/health`);
        if (res.ok) {
            const data = await res.json();
            if (data.status === 'HEALTHY') {
                badge.textContent = 'ONLINE (GPU READY)';
                badge.classList.add('online');
            } else {
                badge.textContent = 'UNHEALTHY';
            }
        } else {
            badge.textContent = 'SERVICE ERROR';
        }
    } catch (e) {
        badge.textContent = 'OFFLINE';
    }
}

function setupInputListeners() {
    const input = document.getElementById('promptInput');
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
}

async function sendMessage() {
    const input = document.getElementById('promptInput');
    const sendBtn = document.getElementById('sendBtn');
    const text = input.value.trim();
    if (!text) return;

    // Render user message
    renderMessage('user', text);
    chatHistory.push({ role: 'user', content: text });
    input.value = '';
    sendBtn.disabled = true;

    const chatBox = document.getElementById('chatBox');
    const loadingId = 'loading-' + Date.now();
    
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message assistant-message';
    loadingDiv.id = loadingId;
    loadingDiv.innerHTML = '<div class="message-content">Thinking...</div>';
    chatBox.appendChild(loadingDiv);
    chatBox.scrollTop = chatBox.scrollHeight;

    try {
        const res = await fetch(`${API_BASE_URL}/v1/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ messages: chatHistory })
        });

        document.getElementById(loadingId).remove();

        if (!res.ok) {
            const err = await res.json();
            renderMessage('assistant', `⚠️ Error: ${err.detail || 'Inference Request Failed'}`);
        } else {
            const data = await res.json();
            renderMessage('assistant', data.response, data.inference);
            chatHistory.push({ role: 'assistant', content: data.response });
        }
    } catch (e) {
        if (document.getElementById(loadingId)) {
            document.getElementById(loadingId).remove();
        }
        renderMessage('assistant', `⚠️ Network / Connection Error: ${e.message}`);
    } finally {
        sendBtn.disabled = false;
        input.focus();
    }
}

function renderMessage(role, content, meta = null) {
    const chatBox = document.getElementById('chatBox');
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}-message`;

    let metaHtml = '';
    if (meta) {
        metaHtml = `<div class="message-meta">Latency: ${meta.latency_seconds}s | Input: ${meta.input_tokens} tok | Output: ${meta.output_tokens} tok | Speed: ${meta.tokens_per_second} tok/s</div>`;
    }

    msgDiv.innerHTML = `<div class="message-content">${escapeHtml(content)}</div>${metaHtml}`;
    chatBox.appendChild(msgDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function clearChat() {
    chatHistory = [];
    const chatBox = document.getElementById('chatBox');
    chatBox.innerHTML = `
        <div class="message assistant-message">
            <div class="message-content">Session cleared. Ready for research queries.</div>
            <div class="message-meta">System • Qualified Contract Lock</div>
        </div>`;
}
