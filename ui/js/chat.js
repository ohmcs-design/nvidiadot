/**
 * DOT AI - Interactive Chat & Copilot Controller
 * Powers conversational pair-programming, thinking stream, and live tool execution.
 */
class ChatController {
  constructor() {
    this.currentAssistantMsgEl = null;
    this.currentThinkingBodyEl = null;
    this.currentContentEl = null;
    this.isStreaming = false;

    this.init();
  }

  init() {
    this.setupTabs();
    this.setupInputs();

    // Listen to chat events from Python backend
    window.onChatEvent = (event) => this.handleChatEvent(event);
  }

  setupTabs() {
    const btnChat = document.getElementById("tab-btn-chat");
    const btnGoals = document.getElementById("tab-btn-goals");
    const viewChat = document.getElementById("view-chat");
    const viewGoals = document.getElementById("view-goals");

    btnChat.onclick = () => {
      btnChat.className = "btn btn-primary";
      btnGoals.className = "btn";
      viewChat.style.display = "flex";
      viewGoals.style.display = "none";
    };

    btnGoals.onclick = () => {
      btnGoals.className = "btn btn-primary";
      btnChat.className = "btn";
      viewGoals.style.display = "flex";
      viewChat.style.display = "none";
    };
  }

  setupInputs() {
    const input = document.getElementById("chat-input");
    const btnSend = document.getElementById("btn-send-chat");
    const btnClear = document.getElementById("btn-clear-chat");

    btnSend.onclick = () => this.sendMessage();

    input.onkeydown = (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        this.sendMessage();
      }
    };

    btnClear.onclick = async () => {
      if (window.pywebview && window.pywebview.api) {
        await window.pywebview.api.reset_chat();
      }
      const container = document.getElementById("chat-messages");
      container.innerHTML = `
        <div class="chat-msg assistant">
          <div class="chat-avatar">DOT</div>
          <div class="chat-bubble">Chat cleared. Kahiye, ab kya naya kaam karna hai?</div>
        </div>
      `;
    };
  }

  updateActiveFileBadge(filePath) {
    const badge = document.getElementById("chat-context-badge");
    const nameEl = document.getElementById("chat-active-file-name");
    if (filePath) {
      nameEl.innerText = filePath.split('/').pop();
      badge.style.display = "flex";
    } else {
      badge.style.display = "none";
    }
  }

  async sendMessage() {
    const input = document.getElementById("chat-input");
    const text = input.value.trim();
    if (!text || this.isStreaming) return;

    input.value = "";
    this.isStreaming = true;
    document.getElementById("btn-send-chat").disabled = true;

    // Append User Message
    this.appendUserMessage(text);

    // Create Assistant Message Placeholder
    this.createAssistantPlaceholder();

    const activeFile = window.codeEditor ? window.codeEditor.activePath : null;

    try {
      if (window.pywebview && window.pywebview.api) {
        await window.pywebview.api.send_chat_message(text, activeFile);
      }
    } catch (e) {
      if (this.currentContentEl) {
        this.currentContentEl.innerHTML += `<div style="color:var(--danger);">Error: ${e}</div>`;
      }
      this.isStreaming = false;
      document.getElementById("btn-send-chat").disabled = false;
    }
  }

  appendUserMessage(text) {
    const container = document.getElementById("chat-messages");
    const msg = document.createElement("div");
    msg.className = "chat-msg user";
    msg.innerHTML = `
      <div class="chat-avatar">ME</div>
      <div class="chat-bubble">${this.escapeHtml(text)}</div>
    `;
    container.appendChild(msg);
    container.scrollTop = container.scrollHeight;
  }

  createAssistantPlaceholder() {
    const container = document.getElementById("chat-messages");
    const msg = document.createElement("div");
    msg.className = "chat-msg assistant";

    msg.innerHTML = `
      <div class="chat-avatar">DOT</div>
      <div class="chat-bubble">
        <div class="thinking-accordion" style="display:none;">
          <div class="thinking-header">
            <span class="thinking-header-text">🧠 Thought Process</span>
            <span class="thinking-toggle-arrow">▶</span>
          </div>
          <div class="thinking-body" style="display:none;"></div>
        </div>
        <div class="chat-response-content"></div>
        <div class="chat-process-pill" style="display:none;"></div>
        <div class="chat-actions-container"></div>
      </div>
    `;

    container.appendChild(msg);
    container.scrollTop = container.scrollHeight;

    this.currentAssistantMsgEl = msg;
    this.currentThinkingBodyEl = msg.querySelector(".thinking-body");
    this.currentContentEl = msg.querySelector(".chat-response-content");
    this.currentProcessPillEl = msg.querySelector(".chat-process-pill");

    // Toggle thinking accordion on click
    const header = msg.querySelector(".thinking-header");
    const body = this.currentThinkingBodyEl;
    const arrow = msg.querySelector(".thinking-toggle-arrow");
    header.onclick = () => {
      const isHidden = body.style.display === "none";
      body.style.display = isHidden ? "block" : "none";
      arrow.textContent = isHidden ? "▼" : "▶";
    };
  }

  handleChatEvent(event) {
    if (!this.currentAssistantMsgEl) return;
    const container = document.getElementById("chat-messages");

    if (event.type === "web_status") {
      let statusEl = this.currentAssistantMsgEl.querySelector(".chat-web-status");
      if (!statusEl) {
        statusEl = document.createElement("div");
        statusEl.className = "chat-web-status";
        statusEl.style.cssText = "font-size:11px; color:#58a6ff; background:#1f2937; padding:4px 8px; border-radius:4px; margin-bottom:6px; display:inline-flex; align-items:center; gap:6px;";
        const bubble = this.currentAssistantMsgEl.querySelector(".chat-bubble");
        bubble.insertBefore(statusEl, bubble.firstChild);
      }
      statusEl.innerHTML = `<span>🌐</span><span>${this.escapeHtml(event.status)}</span>`;
      container.scrollTop = container.scrollHeight;

    } else if (event.type === "reasoning") {
      const accordion = this.currentAssistantMsgEl.querySelector(".thinking-accordion");
      accordion.style.display = "block";
      this.currentThinkingBodyEl.textContent += event.text;
      const headerText = this.currentAssistantMsgEl.querySelector(".thinking-header-text");
      if (headerText) {
        headerText.innerHTML = `🧠 Thought Process <span class="thinking-pulse">⚡ thinking...</span>`;
      }
      if (this.currentThinkingBodyEl.style.display !== "none") {
        this.currentThinkingBodyEl.scrollTop = this.currentThinkingBodyEl.scrollHeight;
      }

    } else if (event.type === "action_in_progress") {
      if (this.currentProcessPillEl) {
        this.currentProcessPillEl.style.display = "flex";
        this.currentProcessPillEl.innerHTML = `
          <div class="process-indicator-spinner"></div>
          <span class="process-indicator-text">${this.escapeHtml(event.status)}</span>
        `;
        container.scrollTop = container.scrollHeight;
      }

    } else if (event.type === "content") {
      // Filter out any markdown code fences from conversational text as safety net
      let text = event.text;
      if (text.includes("```")) {
        text = text.split("```")[0];
      }
      if (text) {
        this.currentContentEl.textContent += text;
        container.scrollTop = container.scrollHeight;
      }

    } else if (event.type === "action_proposal") {
      if (this.currentProcessPillEl) {
        this.currentProcessPillEl.style.display = "none";
      }
      this.renderActionCard(event);
      container.scrollTop = container.scrollHeight;

    } else if (event.type === "done") {
      this.isStreaming = false;
      document.getElementById("btn-send-chat").disabled = false;
      if (this.currentProcessPillEl) {
        this.currentProcessPillEl.style.display = "none";
      }
      const headerText = this.currentAssistantMsgEl ? this.currentAssistantMsgEl.querySelector(".thinking-header-text") : null;
      if (headerText) {
        headerText.textContent = "🧠 Thought Process";
      }
      this.currentAssistantMsgEl = null;
    }
  }

  renderActionCard(action) {
    const actionsContainer = this.currentAssistantMsgEl.querySelector(".chat-actions-container");
    const card = document.createElement("div");

    if (action.action_type === "write_file") {
      card.className = "chat-action-card";
      card.innerHTML = `
        <div class="action-card-header">
          <div class="action-file-badge">
            <span class="action-file-icon">📄</span>
            <span class="action-file-name">${this.escapeHtml(action.path)}</span>
          </div>
          <span class="action-status-badge">Ready to apply</span>
        </div>
        ${action.explanation ? `<div class="action-card-explanation">${this.escapeHtml(action.explanation)}</div>` : ''}
        <div class="action-buttons">
          <button class="btn btn-primary btn-diff-review" style="padding:4px 9px; font-size:11px;">🔍 Review Diff</button>
          <button class="btn btn-accent btn-action-approve" style="padding:4px 9px; font-size:11px;">✓ Approve & Apply</button>
          <button class="btn btn-action-reject" style="padding:4px 9px; font-size:11px; color:var(--danger);">✕ Reject</button>
        </div>
      `;

      card.querySelector(".btn-diff-review").onclick = () => {
        if (window.dotPanel) {
          window.dotPanel.pendingApproval = { id: action.action_id, title: `Update ${action.path}`, details: { unified_diff: action.diff } };
          window.dotPanel.showDiffModal();
        }
      };

      card.querySelector(".btn-action-approve").onclick = async () => {
        const btnApprove = card.querySelector(".btn-action-approve");
        btnApprove.disabled = true;
        btnApprove.innerHTML = `⏳ Applying...`;
        const res = await window.pywebview.api.apply_chat_action(action.action_id);
        if (res.success) {
          card.className = "chat-action-card applied";
          card.innerHTML = `
            <div class="action-applied-banner">
              <span style="color:var(--nvidia-green); font-size:14px; font-weight:bold;">✓</span>
              <span>Applied changes to <b>${this.escapeHtml(action.path)}</b></span>
            </div>
          `;
          if (window.refreshFileTree) window.refreshFileTree();
          if (window.codeEditor) window.codeEditor.openFile(action.path);
        } else {
          alert("Error: " + res.error);
          btnApprove.disabled = false;
          btnApprove.innerHTML = `✓ Approve & Apply`;
        }
      };

      card.querySelector(".btn-action-reject").onclick = async () => {
        await window.pywebview.api.reject_action(action.action_id);
        card.className = "chat-action-card rejected";
        card.innerHTML = `<div class="action-rejected-banner">✕ Action rejected.</div>`;
      };

    } else if (action.action_type === "run_command") {
      card.className = "chat-action-card command";
      card.innerHTML = `
        <div class="action-card-header">
          <div class="action-file-badge">
            <span class="action-file-icon">⚡</span>
            <span>Proposed Shell Command</span>
          </div>
          <span class="action-status-badge">Ready to run</span>
        </div>
        <div style="font-family:var(--font-mono); font-size:11px; background:#000; padding:6px 8px; border-radius:4px; margin:6px 0; border: 1px solid #30363d;">$ ${this.escapeHtml(action.command)}</div>
        ${action.explanation ? `<div class="action-card-explanation">${this.escapeHtml(action.explanation)}</div>` : ''}
        <div class="action-buttons">
          <button class="btn btn-accent btn-action-approve" style="padding:4px 9px; font-size:11px;">⚡ Run Command</button>
          <button class="btn btn-action-reject" style="padding:4px 9px; font-size:11px; color:var(--danger);">✕ Reject</button>
        </div>
      `;

      card.querySelector(".btn-action-approve").onclick = async () => {
        card.innerHTML = `<div style="color:#d29922; font-size:11px;">⏳ Executing command in PowerShell...</div>`;
        const res = await window.pywebview.api.apply_chat_action(action.action_id);
        card.className = "chat-action-card applied";
        card.innerHTML = `
          <div style="color:var(--nvidia-green); font-weight:600; font-size:11px; margin-bottom:4px;">✓ Executed: ${this.escapeHtml(action.command)}</div>
          <pre style="font-family:var(--font-mono); font-size:10px; background:#000; padding:6px; margin:0; max-height:120px; overflow:auto; border-radius:4px;">${this.escapeHtml(res.stdout || '')}${this.escapeHtml(res.stderr || '')}</pre>
        `;
      };

      card.querySelector(".btn-action-reject").onclick = async () => {
        await window.pywebview.api.reject_action(action.action_id);
        card.className = "chat-action-card rejected";
        card.innerHTML = `<div class="action-rejected-banner">✕ Command cancelled.</div>`;
      };
    } else if (action.action_type === "browse_website") {
      card.className = "chat-action-card";
      card.innerHTML = `
        <div class="action-card-header">
          <div class="action-file-badge">
            <span class="action-file-icon">🌐</span>
            <span>Website Inspection: <b>${this.escapeHtml(action.url)}</b></span>
          </div>
        </div>
        ${action.explanation ? `<div class="action-card-explanation">${this.escapeHtml(action.explanation)}</div>` : ''}
        <div class="action-buttons">
          <button class="btn btn-nvidia btn-open-in-browser" style="padding:4px 9px; font-size:11px;">Open in Live Browser</button>
        </div>
      `;
      card.querySelector(".btn-open-in-browser").onclick = () => {
        const toggleBtn = document.getElementById("btn-toggle-browser-tab");
        if (toggleBtn) toggleBtn.click();
        const urlInput = document.getElementById("browser-url-input");
        if (urlInput) {
          urlInput.value = action.url;
          document.getElementById("btn-browser-go").click();
        }
      };
    }

    actionsContainer.appendChild(card);
  }

  escapeHtml(str) {
    return str.replace(/[&<>'"]/g, 
      tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
    );
  }
}

window.chatController = new ChatController();
