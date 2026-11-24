// ==========================================================================
// Contract IQ - Enhanced Interactive Frontend Controller
// Theme Management, Message Micro-Actions, Audio TTS, Filter Controls & Toasts
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {
    initThemeManager();
    initDropZone();
    initUploadForm();
    initChatForm();
    initContractAnalysis();
    initContractFilters();
    initDocDeletion();
    initClearChat();
});

// ----------------- Theme Manager (Light / Dark) -----------------
function initThemeManager() {
    const toggleBtn = document.getElementById('themeToggleBtn');
    const htmlEl = document.documentElement;

    // Retrieve saved theme or default to light for a clean, decent look
    const savedTheme = localStorage.getItem('contract_iq_theme') || 'light';
    htmlEl.setAttribute('data-theme', savedTheme);

    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            const currentTheme = htmlEl.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            htmlEl.setAttribute('data-theme', newTheme);
            localStorage.setItem('contract_iq_theme', newTheme);
            showToast(`Switched to ${newTheme.toUpperCase()} theme`, 'info');
        });
    }
}

// ----------------- Toast Notification System -----------------
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    let icon = 'ℹ️';
    if (type === 'success') icon = '✅';
    if (type === 'error') icon = '❌';

    toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'toastOut 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards';
        setTimeout(() => toast.remove(), 300);
    }, 3200);
}

// ----------------- Quick Question Autofill -----------------
window.setQuestion = function(text) {
    const input = document.getElementById('userInput');
    if (input) {
        input.value = text;
        input.focus();
        showToast('Question loaded into input', 'info');
        // Visual pulse effect
        input.style.transform = 'scale(1.02)';
        setTimeout(() => input.style.transform = 'scale(1)', 200);
    }
};

// ----------------- PDF Upload & DropZone -----------------
function initDropZone() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('pdfFileInput');

    if (!dropZone || !fileInput) return;

    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    ['dragleave', 'dragend'].forEach(type => {
        dropZone.addEventListener(type, () => dropZone.classList.remove('dragover'));
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
            fileInput.files = e.dataTransfer.files;
            updateDropText(fileInput.files[0].name);
        }
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length) {
            updateDropText(fileInput.files[0].name);
        }
    });
}

function updateDropText(filename) {
    const textEl = document.querySelector('.drop-text');
    if (textEl) {
        textEl.innerHTML = `Selected: <strong>${filename}</strong>`;
    }
}

function initUploadForm() {
    const form = document.getElementById('uploadForm');
    const statusEl = document.getElementById('uploadStatus');
    const uploadBtn = document.getElementById('uploadBtn');

    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const fileInput = document.getElementById('pdfFileInput');
        if (!fileInput.files.length) {
            showStatus(statusEl, 'Please select a PDF file first.', 'error');
            return;
        }

        const formData = new FormData();
        formData.append('file', fileInput.files[0]);

        uploadBtn.disabled = true;
        uploadBtn.innerText = 'Extracting & Indexing...';
        showStatus(statusEl, 'Extracting pages and building isolated FAISS vector index...', '');

        try {
            const res = await fetch('/api/documents/upload', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();

            if (res.ok) {
                showToast(`Indexed ${fileInput.files[0].name} (${data.document.page_count} pages)`, 'success');
                showStatus(statusEl, '✅ Upload and indexing successful! Refreshing...', 'success');
                setTimeout(() => window.location.reload(), 700);
            } else {
                showStatus(statusEl, `❌ ${data.detail || 'Upload failed'}`, 'error');
                showToast(data.detail || 'Upload failed', 'error');
                uploadBtn.disabled = false;
                uploadBtn.innerText = 'Upload & Index PDF';
            }
        } catch (err) {
            showStatus(statusEl, `❌ Error: ${err.message}`, 'error');
            showToast(err.message, 'error');
            uploadBtn.disabled = false;
            uploadBtn.innerText = 'Upload & Index PDF';
        }
    });
}

function showStatus(el, msg, type) {
    if (!el) return;
    el.className = `status-msg ${type}`;
    el.innerText = msg;
}

// ----------------- Document Deletion -----------------
function initDocDeletion() {
    document.querySelectorAll('.delete-doc-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.stopPropagation();
            const docId = btn.getAttribute('data-id');
            if (!confirm('Are you sure you want to delete this document from your session?')) return;

            try {
                const res = await fetch(`/api/documents/${docId}`, { method: 'DELETE' });
                if (res.ok) {
                    showToast('Document deleted from session', 'success');
                    setTimeout(() => window.location.reload(), 400);
                } else {
                    showToast('Failed to delete document', 'error');
                }
            } catch (err) {
                showToast(`Error deleting document: ${err.message}`, 'error');
            }
        });
    });
}

// ----------------- Live Chat Interface -----------------
function initChatForm() {
    const chatForm = document.getElementById('chatForm');
    const userInput = document.getElementById('userInput');
    const sendBtn = document.getElementById('sendBtn');
    const chatMessages = document.getElementById('chatMessages');
    const placeholder = document.getElementById('chatPlaceholder');

    if (!chatForm || !userInput) return;

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const text = userInput.value.trim();
        if (!text) return;

        // Hide placeholder
        if (placeholder) placeholder.style.display = 'none';

        // Append user bubble
        appendChatBubble('user', text, 'YOU');
        userInput.value = '';
        sendBtn.disabled = true;

        // Append loading placeholder bubble
        const loadingBubble = appendLoadingBubble();
        chatMessages.scrollTop = chatMessages.scrollHeight;

        try {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });
            const data = await res.json();

            loadingBubble.remove();

            if (res.ok) {
                appendChatBubble('assistant', data.answer, data.query_type || 'CONTRACT IQ', data.sources);
                showToast(`Answered via ${data.query_type || 'RAG Pipeline'}`, 'success');
            } else {
                appendChatBubble('assistant', `⚠️ Error: ${data.detail || 'Could not process query'}`, 'ERROR');
                showToast('Query error', 'error');
            }
        } catch (err) {
            loadingBubble.remove();
            appendChatBubble('assistant', `⚠️ Network error: ${err.message}`, 'ERROR');
            showToast('Network error', 'error');
        } finally {
            sendBtn.disabled = false;
            userInput.focus();
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    });
}

function appendChatBubble(sender, text, queryType, sources = []) {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return null;

    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${sender}`;

    // Convert markdown headers to styled tags
    let formattedText = text
        .replace(/### (.*?)\n/g, '<h3>📌 $1</h3>')
        .replace(/## (.*?)\n/g, '<h3>⚖️ $1</h3>')
        .replace(/\n\n/g, '<br><br>')
        .replace(/\n/g, '<br>');

    let sourcesHtml = '';
    if (sources && sources.length) {
        sourcesHtml = `
            <div class="bubble-sources">
                <strong>Citations & Statutory References:</strong>
                <ul>
                    ${sources.map(s => `
                        <li>
                            ${s.type === 'document' 
                                ? `📄 <strong>Page ${s.page_number}</strong>: ${s.clause || 'Clause'}`
                                : `⚖️ <strong>${s.act_name}</strong>: Sec ${s.section_number} (${s.section_title})`}
                        </li>
                    `).join('')}
                </ul>
            </div>
        `;
    }

    // Interactive Action Toolbar (Copy & Audio Speech)
    let toolbarHtml = '';
    if (sender === 'assistant') {
        toolbarHtml = `
            <div class="bubble-actions-toolbar">
                <button class="action-icon-btn copy-btn" title="Copy answer to clipboard">
                    📋 Copy Advice
                </button>
                <button class="action-icon-btn speech-btn" title="Read explanation aloud">
                    🗣️ Listen
                </button>
                <button class="action-icon-btn print-btn" title="Print advice">
                    🖨️ Print
                </button>
            </div>
        `;
    }

    bubble.innerHTML = `
        <div class="bubble-header">
            <span class="sender-tag">${sender === 'user' ? 'You' : 'Contract IQ'}</span>
            <span class="query-tag">${queryType}</span>
        </div>
        <div class="bubble-body markdown-content">${formattedText}</div>
        ${sourcesHtml}
        ${toolbarHtml}
    `;

    // Attach micro-actions
    if (sender === 'assistant') {
        const copyBtn = bubble.querySelector('.copy-btn');
        if (copyBtn) {
            copyBtn.addEventListener('click', () => {
                navigator.clipboard.writeText(text);
                copyBtn.innerHTML = '✅ Copied!';
                showToast('Advice copied to clipboard', 'success');
                setTimeout(() => copyBtn.innerHTML = '📋 Copy Advice', 2000);
            });
        }

        const speechBtn = bubble.querySelector('.speech-btn');
        if (speechBtn && 'speechSynthesis' in window) {
            let isSpeaking = false;
            speechBtn.addEventListener('click', () => {
                if (isSpeaking) {
                    window.speechSynthesis.cancel();
                    speechBtn.innerHTML = '🗣️ Listen';
                    isSpeaking = false;
                } else {
                    window.speechSynthesis.cancel();
                    const cleanText = text.replace(/[#*`]/g, '');
                    const utter = new SpeechSynthesisUtterance(cleanText);
                    utter.rate = 1.0;
                    utter.onend = () => {
                        speechBtn.innerHTML = '🗣️ Listen';
                        isSpeaking = false;
                    };
                    window.speechSynthesis.speak(utter);
                    speechBtn.innerHTML = '⏹️ Stop';
                    isSpeaking = true;
                    showToast('Reading advice aloud...', 'info');
                }
            });
        }

        const printBtn = bubble.querySelector('.print-btn');
        if (printBtn) {
            printBtn.addEventListener('click', () => {
                const printWin = window.open('', '_blank');
                printWin.document.write(`
                    <html>
                    <head><title>Contract IQ Legal Advice</title>
                    <style>body{font-family:sans-serif;padding:30px;line-height:1.6;color:#111;}</style>
                    </head>
                    <body>
                        <h2>Contract IQ - Grounded Legal Advice</h2>
                        <hr>
                        <div>${formattedText}</div>
                        <br>
                        <p><em>Sources: Indian Statutory Knowledge Base</em></p>
                    </body>
                    </html>
                `);
                printWin.document.close();
                printWin.print();
            });
        }
    }

    chatMessages.appendChild(bubble);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return bubble;
}

function appendLoadingBubble() {
    const chatMessages = document.getElementById('chatMessages');
    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble assistant';
    bubble.innerHTML = `
        <div class="bubble-header">
            <span class="sender-tag">Contract IQ</span>
            <span class="query-tag">ANALYZING</span>
        </div>
        <div class="bubble-body">
            <span class="pulse-text">⚡ Retrieving relevant clauses & synthesizing Indian statutory context...</span>
        </div>
    `;
    chatMessages.appendChild(bubble);
    return bubble;
}

function initClearChat() {
    const clearBtn = document.getElementById('clearChatBtn');
    const clearHistoryBtn = document.getElementById('clearAllHistoryBtn');

    const handleClear = async () => {
        if (!confirm('Are you sure you want to clear this conversation history?')) return;
        try {
            await fetch('/api/chat/clear', { method: 'POST' });
            showToast('Chat history cleared', 'info');
            setTimeout(() => window.location.reload(), 400);
        } catch (err) {
            showToast('Error clearing chat history', 'error');
        }
    };

    if (clearBtn) clearBtn.addEventListener('click', handleClear);
    if (clearHistoryBtn) clearHistoryBtn.addEventListener('click', handleClear);
}

// ----------------- Contract Risk Analysis & Interactive Filter -----------------
function initContractAnalysis() {
    const runBtn = document.getElementById('runAnalysisBtn');
    const docSelect = document.getElementById('analysisDocSelect');
    const loadingEl = document.getElementById('analysisLoading');
    const resultsEl = document.getElementById('analysisResults');
    const emptyNotice = document.getElementById('noAnalysisNotice');

    if (!runBtn || !docSelect) return;

    runBtn.addEventListener('click', async () => {
        const docId = docSelect.value;
        if (!docId) {
            showToast('Please upload or select an agreement first.', 'error');
            return;
        }

        runBtn.disabled = true;
        if (loadingEl) loadingEl.classList.remove('hidden');
        if (resultsEl) resultsEl.classList.add('hidden');
        if (emptyNotice) emptyNotice.classList.add('hidden');

        try {
            const res = await fetch('/api/contracts/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ document_id: docId })
            });
            const data = await res.json();

            if (res.ok) {
                showToast('Risk audit completed successfully!', 'success');
                setTimeout(() => window.location.reload(), 500);
            } else {
                showToast(`Analysis failed: ${data.detail || 'Unknown error'}`, 'error');
                if (loadingEl) loadingEl.classList.add('hidden');
                if (emptyNotice) emptyNotice.classList.remove('hidden');
                runBtn.disabled = false;
            }
        } catch (err) {
            showToast(`Analysis error: ${err.message}`, 'error');
            if (loadingEl) loadingEl.classList.add('hidden');
            if (emptyNotice) emptyNotice.classList.remove('hidden');
            runBtn.disabled = false;
        }
    });
}

function initContractFilters() {
    const filterPills = document.querySelectorAll('.filter-pill');
    if (!filterPills.length) return;

    filterPills.forEach(pill => {
        pill.addEventListener('click', () => {
            filterPills.forEach(p => p.classList.remove('active'));
            pill.classList.add('active');

            const filterValue = pill.getAttribute('data-filter');
            const findingCards = document.querySelectorAll('.finding-card');

            findingCards.forEach(card => {
                if (filterValue === 'all') {
                    card.style.display = 'block';
                } else if (filterValue === 'high') {
                    card.style.display = card.classList.contains('risk-border-high') ? 'block' : 'none';
                } else if (filterValue === 'medium') {
                    card.style.display = card.classList.contains('risk-border-medium') ? 'block' : 'none';
                }
            });
        });
    });
}
