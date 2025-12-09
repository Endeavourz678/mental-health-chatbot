// ============ KONFIGURASI ============
const API_URL = 'http://127.0.0.1:8000';
const MIN_MESSAGES_FOR_ANALYSIS = 5;

// ============ STATE ============
let sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
let messageCount = 0;
let analysisComplete = false;

// ============ ELEMEN DOM ============
const chatForm = document.getElementById('chatForm');
const chatInput = document.getElementById('chatInput');
const chatMessages = document.getElementById('chatMessages');
const chatPlaceholder = document.getElementById('chatPlaceholder');
const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const newChatBtn = document.getElementById('newChatBtn');

// ============ CEK KONEKSI SERVER ============
async function checkServerConnection() {
    try {
        const response = await fetch(API_URL + '/health');
        if (response.ok) {
            if (statusDot) statusDot.classList.remove('offline');
            if (statusText) statusText.textContent = 'Terhubung';
            return true;
        }
    } catch (error) {
        console.error('Server tidak terhubung:', error);
    }
    if (statusDot) statusDot.classList.add('offline');
    if (statusText) statusText.textContent = 'Terputus';
    return false;
}

// ============ UPDATE PROGRESS BAR ============
function updateProgress() {
    const percentage = Math.min((messageCount / MIN_MESSAGES_FOR_ANALYSIS) * 100, 100);
    if (progressFill) progressFill.style.width = percentage + '%';
    
    if (progressText) {
        if (analysisComplete) {
            progressText.textContent = '✅ Analisis selesai!';
            if (progressFill) progressFill.style.background = '#28a745';
        } else if (messageCount >= MIN_MESSAGES_FOR_ANALYSIS) {
            progressText.textContent = '🔍 Menganalisis percakapan...';
        } else {
            const remaining = MIN_MESSAGES_FOR_ANALYSIS - messageCount;
            progressText.textContent = `${remaining} pesan lagi untuk analisis`;
        }
    }
}

// ============ BUAT BUBBLE PESAN ============
function createMessageBubble(text, sender = 'user') {
    const row = document.createElement('div');
    row.classList.add('message-row', sender);

    const bubble = document.createElement('div');
    bubble.classList.add('message-bubble');
    bubble.innerHTML = text.replace(/\n/g, '<br>');

    if (sender === 'assistant') {
        const avatar = document.createElement('div');
        avatar.classList.add('message-avatar');
        avatar.innerHTML = `<img src="friend.jpg" alt="Assistant">`;
        row.appendChild(avatar);
        row.appendChild(bubble);
    } else {
        row.appendChild(bubble);
    }

    return row;
}

// ============ BUAT CARD ANALISIS ============
function createAnalysisCard(classification, confidence, text) {
    const row = document.createElement('div');
    row.classList.add('message-row', 'assistant');

    const avatar = document.createElement('div');
    avatar.classList.add('message-avatar');
    avatar.innerHTML = `<img src="friend.jpg" alt="Assistant">`;

    const card = document.createElement('div');
    card.classList.add('analysis-card');
    
    const confidencePercent = Math.round(confidence * 100);
    const badgeClass = classification ? classification.toLowerCase().replace(' ', '-') : 'normal';

    card.innerHTML = `
        <div class="analysis-header">
            <span class="analysis-title">📊 Hasil Analisis</span>
            <span class="analysis-badge ${badgeClass}">${classification || 'Unknown'}</span>
        </div>
        <div class="analysis-confidence">
            <span>Tingkat keyakinan: ${confidencePercent}%</span>
            <div class="confidence-bar">
                <div class="confidence-fill" style="width: ${confidencePercent}%"></div>
            </div>
        </div>
        <div class="analysis-content">${text.replace(/\n/g, '<br>')}</div>
    `;

    row.appendChild(avatar);
    row.appendChild(card);

    return row;
}

// ============ TAMPILKAN TYPING INDICATOR ============
function showTypingIndicator() {
    const row = document.createElement('div');
    row.classList.add('message-row', 'assistant');
    row.id = 'typingIndicator';

    const avatar = document.createElement('div');
    avatar.classList.add('message-avatar');
    avatar.innerHTML = `<img src="friend.jpg" alt="Assistant">`;

    const bubble = document.createElement('div');
    bubble.classList.add('message-bubble', 'typing-bubble');
    bubble.innerHTML = `
        <div class="typing-dots">
            <span></span>
            <span></span>
            <span></span>
        </div>
    `;

    row.appendChild(avatar);
    row.appendChild(bubble);
    chatMessages.appendChild(row);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ============ SEMBUNYIKAN TYPING INDICATOR ============
function hideTypingIndicator() {
    const typing = document.getElementById('typingIndicator');
    if (typing) typing.remove();
}

// ============ KIRIM PESAN KE API ============
async function sendMessage(text) {
    try {
        const response = await fetch(API_URL + '/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: text,
                session_id: sessionId
            })
        });

        if (response.ok) {
            const data = await response.json();
            console.log('Response dari server:', data);
            return data;
        } else {
            const error = await response.json();
            console.error('Error dari server:', error);
            throw new Error(error.detail || 'Terjadi kesalahan');
        }
    } catch (error) {
        console.error('Fetch error:', error);
        throw error;
    }
}

// ============ HANDLE SUBMIT FORM ============
chatForm.addEventListener('submit', async function(e) {
    e.preventDefault();

    const text = chatInput.value.trim();
    if (!text) return;

    // Hapus placeholder jika ada
    if (chatPlaceholder) {
        chatPlaceholder.remove();
    }

    // Tambah pesan user
    const userBubble = createMessageBubble(text, 'user');
    chatMessages.appendChild(userBubble);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Reset input & disable
    chatInput.value = '';
    chatInput.disabled = true;

    // Update counter
    messageCount++;
    updateProgress();

    // Tampilkan typing indicator
    showTypingIndicator();

    try {
        // Kirim ke API
        const data = await sendMessage(text);

        // Sembunyikan typing
        hideTypingIndicator();

        // Tampilkan response
        if (data.is_final_analysis && data.classification) {
            // Tampilkan card analisis
            analysisComplete = true;
            const analysisCard = createAnalysisCard(
                data.classification,
                data.confidence,
                data.response
            );
            chatMessages.appendChild(analysisCard);
        } else {
            // Tampilkan pesan biasa
            const assistantBubble = createMessageBubble(data.response, 'assistant');
            chatMessages.appendChild(assistantBubble);
        }

        updateProgress();

    } catch (error) {
        hideTypingIndicator();
        const errorBubble = createMessageBubble(
            'Maaf, terjadi kesalahan koneksi. Pastikan server berjalan.',
            'assistant'
        );
        chatMessages.appendChild(errorBubble);
    }

    // Enable input kembali
    chatInput.disabled = false;
    chatInput.focus();
    chatMessages.scrollTop = chatMessages.scrollHeight;
});

// ============ NEW CHAT ============
function newChat() {
    sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    messageCount = 0;
    analysisComplete = false;
    
    // Reset chat messages
    chatMessages.innerHTML = `
        <div class="chat-placeholder" id="chatPlaceholder">
            Belum ada percakapan. Kamu bisa mulai dengan menceritakan perasaanmu di sini.
        </div>
    `;
    
    // Reset progress
    if (progressFill) {
        progressFill.style.width = '0%';
        progressFill.style.background = 'linear-gradient(135deg, #c8ff00, #a8e000)';
    }
    updateProgress();
    
    chatInput.focus();
}

// ============ EVENT LISTENER UNTUK NEW CHAT BUTTON ============
if (newChatBtn) {
    newChatBtn.addEventListener('click', newChat);
}

// ============ INISIALISASI ============
checkServerConnection();
setInterval(checkServerConnection, 30000); // Cek setiap 30 detik
updateProgress();