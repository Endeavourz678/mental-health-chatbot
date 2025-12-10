// ============================================
// MindCare Chatbot - Frontend Script
// Chat mengalir TERUS tanpa ending
// Status ditampilkan real-time
// User SELALU bisa chat terus
// ============================================

const API_URL = 'http://127.0.0.1:8000';

// State
let sessionId = generateSessionId();
let isProcessing = false;  // Flag untuk prevent double submit

// DOM Elements
let chatForm, chatInput, chatMessages, statusBadge, statusLabelText;
let statusDot, statusText, sendBtn, newChatBtn;

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    // Get DOM elements
    chatForm = document.getElementById('chatForm');
    chatInput = document.getElementById('chatInput');
    chatMessages = document.getElementById('chatMessages');
    statusBadge = document.getElementById('statusBadge');
    statusLabelText = document.getElementById('statusLabelText');
    statusDot = document.getElementById('statusDot');
    statusText = document.getElementById('statusText');
    sendBtn = document.getElementById('sendBtn');
    newChatBtn = document.getElementById('newChatBtn');
    
    // Setup event listeners
    setupEventListeners();
    
    // Check connection
    checkConnection();
    setInterval(checkConnection, 30000);
    
    // Focus input
    if (chatInput) chatInput.focus();
    
    // Initial status
    updateStatusBadge(null, 0, false);
    
    console.log('MindCare initialized!');
});

// ============================================
// EVENT LISTENERS SETUP
// ============================================

function setupEventListeners() {
    // Form submit
    if (chatForm) {
        chatForm.addEventListener('submit', handleSubmit);
    }
    
    // New chat button
    if (newChatBtn) {
        newChatBtn.addEventListener('click', handleNewChat);
    }
    
    // Enter key to send
    if (chatInput) {
        chatInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
            }
        });
    }
}

// ============================================
// UTILITY FUNCTIONS
// ============================================

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

// ============================================
// SERVER CONNECTION
// ============================================

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

// ============================================
// STATUS BADGE UPDATE
// ============================================

function updateStatusBadge(classification, confidence, showLabel) {
    if (!statusBadge || !statusLabelText) return;
    
    // Reset all classes
    statusBadge.className = 'status-badge';
    
    if (showLabel && classification && classification !== 'Normal') {
        const confidencePct = Math.round(confidence * 100);
        statusLabelText.textContent = `${classification} (${confidencePct}%)`;
        
        // Add class based on classification
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

// ============================================
// MESSAGE CREATION
// ============================================

function createMessageElement(text, sender, statusLabel) {
    const row = document.createElement('div');
    row.className = `message-row ${sender}`;
    
    // Avatar
    const avatar = document.createElement('div');
    avatar.className = 'msg-avatar';
    
    if (sender === 'assistant') {
        avatar.innerHTML = '<img src="friend.jpg" alt="MindCare">';
    } else {
        avatar.className += ' user-avatar';
        avatar.textContent = '👤';
    }
    
    // Content container
    const content = document.createElement('div');
    content.className = 'msg-content';
    
    // Bubble
    const bubble = document.createElement('div');
    bubble.className = 'msg-bubble';
    bubble.innerHTML = text.replace(/\n/g, '<br>');
    content.appendChild(bubble);
    
    // Status label (hanya untuk assistant dan jika ada)
    if (sender === 'assistant' && statusLabel) {
        const label = document.createElement('div');
        label.className = 'msg-status-label';
        label.innerHTML = `<span class="label-icon">📊</span> Status saat ini: <strong>${statusLabel}</strong>`;
        content.appendChild(label);
    }
    
    // Assemble
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

// ============================================
// SEND MESSAGE TO API
// ============================================

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

// ============================================
// HANDLE FORM SUBMIT
// ============================================

async function handleSubmit(e) {
    if (e) e.preventDefault();
    
    // Prevent double submit
    if (isProcessing) {
        console.log('Already processing, please wait...');
        return;
    }
    
    const message = chatInput ? chatInput.value.trim() : '';
    if (!message) return;
    
    // Clear input and disable temporarily
    if (chatInput) chatInput.value = '';
    disableInput();
    
    // Remove welcome message if exists
    removeWelcomeMessage();
    
    // Add user message to chat
    const userMsg = createMessageElement(message, 'user', null);
    if (chatMessages) {
        chatMessages.appendChild(userMsg);
        scrollToBottom();
    }
    
    // Show typing indicator
    const typing = createTypingIndicator();
    if (chatMessages) {
        chatMessages.appendChild(typing);
        scrollToBottom();
    }
    
    try {
        // Send to API
        console.log('Sending message:', message);
        const data = await sendMessageToAPI(message);
        console.log('Received response:', data);
        
        // Remove typing indicator
        removeTypingIndicator();
        
        // Update status badge in navbar
        updateStatusBadge(data.classification, data.confidence, data.show_label);
        
        // Create status label text if should show
        const statusLabel = data.show_label ? data.status_label : null;
        
        // Add assistant message
        const assistantMsg = createMessageElement(data.response, 'assistant', statusLabel);
        if (chatMessages) {
            chatMessages.appendChild(assistantMsg);
            scrollToBottom();
        }
        
    } catch (error) {
        console.error('Error sending message:', error);
        removeTypingIndicator();
        
        // Show error message
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
    
    // ALWAYS re-enable input - this is critical!
    enableInput();
}

// ============================================
// HANDLE NEW CHAT
// ============================================

function handleNewChat() {
    // Generate new session
    sessionId = generateSessionId();
    
    // Clear messages and show welcome
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
    
    // Reset status badge
    updateStatusBadge(null, 0, false);
    
    // Enable and focus input
    enableInput();
    
    console.log('New chat started with session:', sessionId);
}

// ============================================
// EXPOSE FUNCTIONS GLOBALLY (for debugging)
// ============================================

window.MindCare = {
    sendMessage: handleSubmit,
    newChat: handleNewChat,
    checkConnection: checkConnection,
    getSessionId: () => sessionId,
    enableInput: enableInput
};