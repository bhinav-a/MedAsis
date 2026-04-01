/* ═══════════════════════════════════════════════════════════════════
   MedStore — Frontend JavaScript
   ═══════════════════════════════════════════════════════════════════ */

// ─── DOM References ─────────────────────────────────────────────────
const tabBtns = document.querySelectorAll('.tab-btn');
const tabSections = document.querySelectorAll('.tab-section');
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const previewImg = document.getElementById('preview-image');
const uploadBtn = document.getElementById('upload-btn');
const uploadResult = document.getElementById('upload-result');
const resultGrid = document.getElementById('result-grid');
const resultTitle = document.getElementById('result-title');
const resultBadge = document.getElementById('result-badge');
const expiryWarning = document.getElementById('expiry-warning');
const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const chatSend = document.getElementById('chat-send');
const alertBanner = document.getElementById('alert-banner');
const alertTitle = document.getElementById('alert-title');
const alertText = document.getElementById('alert-text');
const inventoryBadge = document.getElementById('inventory-badge');

let selectedFile = null;

// ─── Tabs ───────────────────────────────────────────────────────────
tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        const tab = btn.dataset.tab;
        tabBtns.forEach(b => b.classList.remove('active'));
        tabSections.forEach(s => s.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById(`section-${tab}`).classList.add('active');
        if (tab === 'inventory') loadInventory();
    });
});

// ─── Drag & Drop ────────────────────────────────────────────────────
dropZone.addEventListener('click', () => fileInput.click());

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    const files = e.dataTransfer.files;
    if (files.length > 0) handleFile(files[0]);
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) handleFile(e.target.files[0]);
});

function handleFile(file) {
    if (!file.type.startsWith('image/')) {
        showAlert('Invalid File', 'Please upload an image file (PNG, JPG, WEBP, etc.).');
        return;
    }
    selectedFile = file;
    const reader = new FileReader();
    reader.onload = (e) => {
        previewImg.src = e.target.result;
        previewImg.classList.remove('hidden');
    };
    reader.readAsDataURL(file);
    uploadBtn.classList.remove('hidden');
    uploadBtn.disabled = false;
}

// ─── Upload ─────────────────────────────────────────────────────────
uploadBtn.addEventListener('click', uploadMedicine);

async function uploadMedicine() {
    if (!selectedFile) return;

    setLoading(uploadBtn, true);
    uploadResult.classList.add('hidden');

    const formData = new FormData();
    formData.append('image', selectedFile);

    try {
        const res = await fetch('/upload', { method: 'POST', body: formData });
        const data = await res.json();

        if (!res.ok || data.error) {
            showAlert('Upload Error', data.error || 'Something went wrong');
            return;
        }

        // Show result
        uploadResult.classList.remove('hidden');
        resultTitle.textContent = data.is_update ? '♻️ Medicine Updated' : '✅ Medicine Added';

        // Badge
        const expiry = data.expiry;
        resultBadge.className = 'status-badge';
        if (data.is_update) {
            resultBadge.textContent = 'Updated';
            resultBadge.classList.add('updated');
        } else if (expiry.status === 'expired') {
            resultBadge.textContent = 'Expired';
            resultBadge.classList.add('expired');
        } else if (expiry.status === 'expiring_soon') {
            resultBadge.textContent = 'Expiring Soon';
            resultBadge.classList.add('expiring');
        } else {
            resultBadge.textContent = 'Valid';
            resultBadge.classList.add('ok');
        }

        // Result grid
        const med = data.medicine;
        const fields = [
            { label: 'Name', value: med.name },
            { label: 'Dose', value: med.dose },
            { label: 'MFD', value: med.mfd },
            { label: 'Expiry', value: med.exp_date },
            { label: 'Batch No', value: med.batch_no },
            { label: 'Manufacturer', value: med.manufacturer },
        ];

        resultGrid.innerHTML = fields.map(f => `
            <div class="result-item">
                <div class="result-label">${f.label}</div>
                <div class="result-value">${f.value}</div>
            </div>
        `).join('');

        // Expiry warning
        expiryWarning.classList.add('hidden');
        if (expiry.status === 'expired') {
            expiryWarning.className = 'expiry-warning danger';
            expiryWarning.textContent = `🚨 This medicine is EXPIRED (${Math.abs(expiry.days)} days ago). Do NOT use it!`;
            expiryWarning.classList.remove('hidden');
        } else if (expiry.status === 'expiring_soon') {
            expiryWarning.className = 'expiry-warning warn';
            expiryWarning.textContent = `⚠️ This medicine expires in ${expiry.days} days. Use it soon or replace it.`;
            expiryWarning.classList.remove('hidden');
        }

        // Refresh inventory count
        loadInventoryCount();

    } catch (err) {
        showAlert('Network Error', err.message);
    } finally {
        setLoading(uploadBtn, false);
    }
}

// ─── Chat ───────────────────────────────────────────────────────────
chatSend.addEventListener('click', sendChat);
chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendChat();
    }
});

async function sendChat() {
    const question = chatInput.value.trim();
    if (!question) return;

    // Remove welcome message
    const welcome = chatMessages.querySelector('.chat-welcome');
    if (welcome) welcome.remove();

    // Add user bubble
    addChatBubble(question, 'user');
    chatInput.value = '';
    setLoading(chatSend, true);

    try {
        const res = await fetch('/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question })
        });
        const data = await res.json();

        if (!res.ok || data.error) {
            addChatBubble(`Error: ${data.error || 'Something went wrong'}`, 'assistant');
            return;
        }

        // Add assistant answer
        let answerHtml = window.marked ? marked.parse(data.answer) : escapeHtml(data.answer);

        // Add source tags
        if (data.sources && data.sources.length > 0) {
            const tags = data.sources
                .filter(s => s.name && s.name !== 'Unknown' && s.name !== '')
                .map(s => `<span class="source-tag">📦 ${escapeHtml(s.name)}</span>`)
                .join('');
            if (tags) answerHtml += '\n' + tags;
        }

        addChatBubble(answerHtml, 'assistant', true);

    } catch (err) {
        addChatBubble(`Network Error: ${err.message}`, 'assistant');
    } finally {
        setLoading(chatSend, false);
    }
}

function addChatBubble(content, role, isHtml = false) {
    const div = document.createElement('div');
    div.className = `chat-bubble ${role}`;
    if (isHtml) {
        div.innerHTML = content;
    } else {
        div.textContent = content;
    }
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ─── Inventory ──────────────────────────────────────────────────────
async function loadInventory() {
    const list = document.getElementById('medicine-list');

    try {
        const res = await fetch('/medicines');
        const data = await res.json();

        if (!data.success) {
            list.innerHTML = '<p class="empty-state">Error loading medicines.</p>';
            return;
        }

        const medicines = data.medicines || [];
        updateStats(medicines);

        if (medicines.length === 0) {
            list.innerHTML = '<p class="empty-state">No medicines in inventory. Upload a medicine image to get started!</p>';
            return;
        }

        list.innerHTML = medicines.map(med => {
            const meta = med.metadata || {};
            const status = med.expiry_status || 'unknown';
            const days = med.days_until_expiry;

            let statusBadge = '';
            let cardClass = 'med-card';
            let icon = '💊';

            if (status === 'expired') {
                statusBadge = '<span class="status-badge expired">Expired</span>';
                cardClass += ' expired-card';
                icon = '⛔';
            } else if (status === 'expiring_soon') {
                statusBadge = `<span class="status-badge expiring">${days}d left</span>`;
                cardClass += ' expiring-card';
                icon = '⚠️';
            } else if (status === 'expiring_warning') {
                statusBadge = `<span class="status-badge expiring">${days}d left</span>`;
                icon = '🔶';
            } else if (status === 'ok') {
                statusBadge = '<span class="status-badge ok">Valid</span>';
            }

            return `
                <div class="${cardClass}">
                    <div class="med-icon">${icon}</div>
                    <div class="med-info">
                        <div class="med-name">${escapeHtml(meta.name || 'Unknown Medicine')}</div>
                        <div class="med-details">
                            ${meta.dose ? `💉 ${escapeHtml(meta.dose)}` : ''}
                            ${meta.exp_date ? ` · 📅 Exp: ${escapeHtml(meta.exp_date)}` : ''}
                            ${meta.manufacturer ? ` · 🏭 ${escapeHtml(meta.manufacturer)}` : ''}
                        </div>
                    </div>
                    <div class="med-actions">
                        ${statusBadge}
                        <button class="btn btn-danger" onclick="deleteMedicine('${escapeHtml(med.id)}')">🗑</button>
                    </div>
                </div>
            `;
        }).join('');

    } catch (err) {
        list.innerHTML = `<p class="empty-state">Error: ${err.message}</p>`;
    }
}

function updateStats(medicines) {
    const total = medicines.length;
    let ok = 0, expiring = 0, expired = 0;
    medicines.forEach(m => {
        const s = m.expiry_status;
        if (s === 'expired') expired++;
        else if (s === 'expiring_soon' || s === 'expiring_warning') expiring++;
        else ok++;
    });

    document.getElementById('stat-total').textContent = total;
    document.getElementById('stat-ok').textContent = ok;
    document.getElementById('stat-expiring').textContent = expiring;
    document.getElementById('stat-expired').textContent = expired;
}

async function loadInventoryCount() {
    try {
        const res = await fetch('/medicines');
        const data = await res.json();
        if (data.success) {
            const count = data.count || 0;
            inventoryBadge.textContent = count;
            if (count > 0) inventoryBadge.classList.remove('hidden');
            else inventoryBadge.classList.add('hidden');
        }
    } catch (_) { /* ignore */ }
}

async function deleteMedicine(id) {
    if (!confirm('Delete this medicine from inventory?')) return;
    try {
        const res = await fetch(`/medicines/${id}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            loadInventory();
            loadInventoryCount();
        } else {
            showAlert('Error', data.error || 'Could not delete');
        }
    } catch (err) {
        showAlert('Error', err.message);
    }
}

// ─── Alerts ─────────────────────────────────────────────────────────
function showAlert(title, text) {
    alertTitle.textContent = title;
    alertText.textContent = text;
    alertBanner.classList.remove('hidden');
}

function dismissAlert() {
    alertBanner.classList.add('hidden');
}

// ─── Helpers ────────────────────────────────────────────────────────
function setLoading(btn, loading) {
    const text = btn.querySelector('.btn-text');
    const loader = btn.querySelector('.btn-loader');
    if (loading) {
        text.classList.add('hidden');
        loader.classList.remove('hidden');
        btn.disabled = true;
    } else {
        text.classList.remove('hidden');
        loader.classList.add('hidden');
        btn.disabled = false;
    }
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// ─── Check for expiring on load ─────────────────────────────────────
async function checkExpiryAlerts() {
    try {
        const res = await fetch('/expiring?days=30');
        const data = await res.json();
        if (!data.success) return;

        const total = (data.expiring_count || 0) + (data.expired_count || 0);
        if (total > 0) {
            const parts = [];
            if (data.expired_count > 0) parts.push(`${data.expired_count} expired`);
            if (data.expiring_count > 0) parts.push(`${data.expiring_count} expiring soon`);
            showAlert('⚠️ Medicine Alert', `You have ${parts.join(' and ')} medicine(s). Check your inventory!`);
        }
    } catch (_) { /* ignore */ }
}

// ─── Init ───────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    loadInventoryCount();
    checkExpiryAlerts();
});
