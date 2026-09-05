/* ============================================================
   Patient Intake Triage Assistant — Frontend Logic
   ============================================================ */

let sessionId = null;
let messageCount = 0;
let sessionEnded = false;

// ── Session Management ─────────────────────────────────────

async function startNewSession() {
  // Reset state
  sessionId = null;
  messageCount = 0;
  sessionEnded = false;

  // Hide triage note, start screen; show input
  document.getElementById('startScreen')?.remove();
  document.getElementById('triageNotePanel').style.display = 'none';
  document.getElementById('inputArea').style.display = 'block';

  // Clear chat area
  const chatArea = document.getElementById('chatArea');
  chatArea.innerHTML = '';

  // Update sidebar
  setStatus('active', 'Active');
  document.getElementById('session-id-display').textContent = '...';
  document.getElementById('msg-count').textContent = '0';

  // Show typing indicator while waiting for greeting
  showTyping();

  try {
    const res = await fetch('/api/start', { method: 'POST', headers: { 'Content-Type': 'application/json' } });
    const data = await res.json();
    removeTyping();

    if (data.error) {
      appendMessage('assistant', `⚠ Error: ${data.error}`);
      setStatus('error', 'Error');
      return;
    }

    sessionId = data.session_id;
    document.getElementById('session-id-display').textContent = sessionId.substring(0, 8) + '...';
    appendMessage('assistant', data.message);
    focusInput();

  } catch (err) {
    removeTyping();
    appendMessage('assistant', '⚠ Failed to connect to the server. Make sure Flask is running.');
    setStatus('error', 'Error');
  }
}

// ── Send Message ───────────────────────────────────────────

async function sendMessage() {
  if (!sessionId || sessionEnded) return;

  const input = document.getElementById('userInput');
  const text = input.value.trim();
  if (!text) return;

  // Clear input
  input.value = '';
  input.style.height = 'auto';

  // Show user message
  appendMessage('user', text);
  messageCount++;
  document.getElementById('msg-count').textContent = messageCount;

  // Disable send while waiting
  setSendEnabled(false);
  showTyping();

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, message: text }),
    });
    const data = await res.json();
    removeTyping();

    if (data.error) {
      appendMessage('assistant', `⚠ ${data.error}`);
      setSendEnabled(true);
      return;
    }

    // Show assistant message
    if (data.message) {
      appendMessage('assistant', data.message);
    }

    // Show triage note if generated
    if (data.note) {
      renderTriageNote(data.note);
      sessionEnded = true;
      setStatus('done', 'Complete');
      setSendEnabled(false);
      input.placeholder = 'Triage session complete. Click "New Session" to start again.';
    } else {
      setSendEnabled(true);
      focusInput();
    }

  } catch (err) {
    removeTyping();
    appendMessage('assistant', '⚠ Network error. Please try again.');
    setSendEnabled(true);
  }
}

// ── Triage Note Renderer ───────────────────────────────────

function renderTriageNote(note) {
  const panel = document.getElementById('triageNotePanel');
  const badge = document.getElementById('urgency-badge');
  const body  = document.getElementById('noteBody');

  // Set urgency badge
  const lvl = note.urgency_level;
  let badgeText, badgeClass;
  if      (lvl === 1) { badgeText = 'LEVEL 1 — IMMEDIATE';     badgeClass = 'urgency-l1'; }
  else if (lvl === 2) { badgeText = 'LEVEL 2 — EMERGENT';      badgeClass = 'urgency-l2'; }
  else if (lvl === 3) { badgeText = 'LEVEL 3 — URGENT';        badgeClass = 'urgency-l3'; }
  else if (lvl === 4) { badgeText = 'LEVEL 4/5 — LESS URGENT'; badgeClass = 'urgency-l4'; }
  else                { badgeText = 'HUMAN REVIEW REQUIRED';    badgeClass = 'urgency-esc'; }

  badge.textContent = badgeText;
  badge.className = `urgency-badge ${badgeClass}`;

  // Format note body with markdown-like bold
  body.innerHTML = formatNoteMarkdown(note.raw);

  panel.style.display = 'block';
  panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function formatNoteMarkdown(text) {
  // Bold **...**
  text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  // Escape HTML except our bold tags (already done above)
  return text;
}

// ── Chat Helpers ───────────────────────────────────────────

function appendMessage(role, text) {
  const chatArea = document.getElementById('chatArea');

  const wrapper = document.createElement('div');
  wrapper.className = `msg ${role}`;

  const avatar = document.createElement('div');
  avatar.className = 'msg-avatar';

  if (role === 'assistant') {
    avatar.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>`;
  } else {
    avatar.textContent = 'P';
  }

  const content = document.createElement('div');
  content.className = 'msg-content';
  content.textContent = text;

  wrapper.appendChild(avatar);
  wrapper.appendChild(content);
  chatArea.appendChild(wrapper);

  chatArea.scrollTop = chatArea.scrollHeight;
}

function showTyping() {
  const chatArea = document.getElementById('chatArea');
  const wrapper = document.createElement('div');
  wrapper.className = 'msg assistant';
  wrapper.id = 'typing-indicator-msg';

  const avatar = document.createElement('div');
  avatar.className = 'msg-avatar';
  avatar.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>`;

  const content = document.createElement('div');
  content.className = 'msg-content';
  content.innerHTML = `<div class="typing-indicator"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div>`;

  wrapper.appendChild(avatar);
  wrapper.appendChild(content);
  chatArea.appendChild(wrapper);
  chatArea.scrollTop = chatArea.scrollHeight;
}

function removeTyping() {
  document.getElementById('typing-indicator-msg')?.remove();
}

// ── UI Helpers ─────────────────────────────────────────────

function setStatus(type, label) {
  const el = document.getElementById('session-status');
  el.textContent = label;
  el.className = `status-badge status-${type}`;
}

function setSendEnabled(enabled) {
  document.getElementById('sendBtn').disabled = !enabled;
}

function focusInput() {
  document.getElementById('userInput').focus();
}

function handleKeyDown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 140) + 'px';
}
