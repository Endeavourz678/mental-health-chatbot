const API_URL = 'http://127.0.0.1:8000';

let sessionId = generateSessionId();
let isProcessing = false;

let chatForm, chatInput, chatMessages, statusBadge, statusLabelText;
let statusDot, statusText, sendBtn, newChatBtn;

document.addEventListener('DOMContentLoaded', function() {
    chatForm = document.getElementById('chatForm');
    chatInput = document.getElementById('chatInput');
    chatMessages = document.getElementById('chatMessages');
    statusBadge = document.getElementById('statusBadge');
    statusLabelText = document.getElementById('statusLabelText');
    statusDot = document.getElementById('statusDot');
    statusText = document.getElementById('statusText');
    sendBtn = document.getElementById('sendBtn');
    newChatBtn = document.getElementById('newChatBtn');
    
    setupEventListeners();
    
    checkConnection();
    setInterval(checkConnection, 30000);
    
    if (chatInput) chatInput.focus();
    
    updateStatusBadge(null, 0, false);
    
    console.log('MindCare initialized!');
});

function setupEventListeners() {
    if (chatForm) {
        chatForm.addEventListener('submit', handleSubmit);
    }
    if (newChatBtn) {
        newChatBtn.addEventListener('click', handleNewChat);
    }
    if (chatInput) {
        chatInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
            }
        });
    }
}

function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

function scrollToBottom() {
    if (chatMessages) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

function enableInput() {
    if (chatInput) {
        chatInput.disabled = false;
        chatInput.focus();
    }
    if (sendBtn) {
        sendBtn.disabled = false;
    }
    isProcessing = false;
}

function disableInput() {
    if (chatInput) chatInput.disabled = true;
    if (sendBtn) sendBtn.disabled = true;
    isProcessing = true;
}

async function checkConnection() {
    try {
        const response = await fetch(`${API_URL}/health`, { 
            method: 'GET',
            timeout: 5000 
        });
        if (response.ok) {
            if (statusDot) statusDot.classList.remove('offline');
            if (statusText) statusText.textContent = 'Online';
            return true;
        }
    } catch (e) {
        console.log('Connection check failed:', e.message);
    }
    if (statusDot) statusDot.classList.add('offline');
    if (statusText) statusText.textContent = 'Offline';
    return false;
}

function updateStatusBadge(classification, confidence, showLabel) {
    if (!statusBadge || !statusLabelText) return;
    statusBadge.className = 'status-badge';
    
    if (showLabel && classification && classification !== 'Normal') {
        const confidencePct = Math.round(confidence * 100);
        statusLabelText.textContent = `${classification} (${confidencePct}%)`;
        const classMap = {
            'Anxiety': 'anxiety',
            'Depression': 'depression',
            'Stress': 'stress',
            'Bipolar': 'bipolar',
            'Personality Disorder': 'personality-disorder',
            'Suicidal': 'suicidal',
            'Normal': 'normal'
        };
        
        const badgeClass = classMap[classification] || 'listening';
        statusBadge.classList.add(badgeClass);
    } else {
        statusLabelText.textContent = 'Mendengarkan...';
        statusBadge.classList.add('listening');
    }
}

function createMessageElement(text, sender, statusLabel) {
    const row = document.createElement('div');
    row.className = `message-row ${sender}`;

    const avatar = document.createElement('div');
    avatar.className = 'msg-avatar';
    
    if (sender === 'assistant') {
        avatar.innerHTML = '<img src="friend.jpg" alt="MindCare">';
    } else {
        avatar.className += ' user-avatar';
        avatar.textContent = '👤';
    }
     const content = document.createElement('div');
    content.className = 'msg-content';
    
    const bubble = document.createElement('div');
    bubble.className = 'msg-bubble';
    bubble.innerHTML = text.replace(/\n/g, '<br>');
    content.appendChild(bubble);
    
    if (sender === 'assistant' && statusLabel) {
        const label = document.createElement('div');
        label.className = 'msg-status-label';
        label.innerHTML = `<span class="label-icon">📊</span> Status saat ini: <strong>${statusLabel}</strong>`;
        content.appendChild(label);
    }
    
    row.appendChild(avatar);
    row.appendChild(content);
    
    return row;
}

function createTypingIndicator() {
    const row = document.createElement('div');
    row.className = 'message-row assistant';
    row.id = 'typingIndicator';
    
    const avatar = document.createElement('div');
    avatar.className = 'msg-avatar';
    avatar.innerHTML = '<img src="friend.jpg" alt="MindCare">';
    
    const typing = document.createElement('div');
    typing.className = 'typing-indicator';
    typing.innerHTML = '<span></span><span></span><span></span>';
    
    row.appendChild(avatar);
    row.appendChild(typing);
    
    return row;
}

function removeTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    if (indicator) indicator.remove();
}

function removeWelcomeMessage() {
    const welcome = document.getElementById('welcomeMessage');
    if (welcome) welcome.remove();
}

async function sendMessageToAPI(message) {
    const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            message: message,
            session_id: sessionId
        })
    });
    
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Server error');
    }
    
    return await response.json();
}

async function handleSubmit(e) {
    if (e) e.preventDefault();
    
    if (isProcessing) {
        console.log('Already processing, please wait...');
        return;
    }
    
    const message = chatInput ? chatInput.value.trim() : '';
    if (!message) return;
    
    if (chatInput) chatInput.value = '';
    disableInput();
    
    removeWelcomeMessage();
    
    const userMsg = createMessageElement(message, 'user', null);
    if (chatMessages) {
        chatMessages.appendChild(userMsg);
        scrollToBottom();
    }
    
    const typing = createTypingIndicator();
    if (chatMessages) {
        chatMessages.appendChild(typing);
        scrollToBottom();
    }
    
    try {
        console.log('Sending message:', message);
        const data = await sendMessageToAPI(message);
        console.log('Received response:', data);
        
        removeTypingIndicator();
        
        updateStatusBadge(data.classification, data.confidence, data.show_label);
        
        const statusLabel = data.show_label ? data.status_label : null;
        
        const assistantMsg = createMessageElement(data.response, 'assistant', statusLabel);
        if (chatMessages) {
            chatMessages.appendChild(assistantMsg);
            scrollToBottom();
        }
        
    } catch (error) {
        console.error('Error sending message:', error);
        removeTypingIndicator();
        
        const errorMsg = createMessageElement(
            '😔 Maaf, terjadi kesalahan koneksi. Pastikan server sedang berjalan. Kamu tetap bisa coba kirim pesan lagi.',
            'assistant',
            null
        );
        if (chatMessages) {
            chatMessages.appendChild(errorMsg);
            scrollToBottom();
        }
    }
    
    enableInput();
}

function handleNewChat() {
    sessionId = generateSessionId();
    
    if (chatMessages) {
        chatMessages.innerHTML = `
            <div class="welcome-message" id="welcomeMessage">
                <div class="welcome-icon">👋</div>
                <h2>Hai! Selamat datang di MindCare</h2>
                <p>Aku di sini untuk mendengarkan ceritamu. Kamu bisa berbagi apa saja yang sedang kamu rasakan - senang, sedih, cemas, atau apapun itu.</p>
                <p class="welcome-hint">Percakapan ini bersifat privat dan aku tidak akan menghakimi apapun yang kamu ceritakan.</p>
            </div>
        `;
    }
    
    updateStatusBadge(null, 0, false);
    
    enableInput();
    
    console.log('New chat started with session:', sessionId);
}


window.MindCare = {
    sendMessage: handleSubmit,
    newChat: handleNewChat,
    checkConnection: checkConnection,
    getSessionId: () => sessionId,
    enableInput: enableInput
};