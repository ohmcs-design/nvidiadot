/**
 * DOT AI - Main Application Controller
 * Handles File Explorer, Terminal Runner, Search Modal, and Settings.
 */
document.addEventListener("DOMContentLoaded", () => {
  // Initialize resizers & panel toggles immediately on DOM load
  setupResizers();
  setupPanelToggles();

  // Wait for pywebview
  window.addEventListener('pywebviewready', () => {
    initApp();
  });
  // Fallback if pywebviewready already fired
  if (window.pywebview && window.pywebview.api) {
    initApp();
  }
});

async function initApp() {
  await loadWorkspace();
  setupTerminal();
  setupSearch();
  setupSettings();
}

async function loadWorkspace() {
  if (!window.pywebview || !window.pywebview.api) return;

  const info = await window.pywebview.api.get_workspace_info();
  updateWorkspaceUI(info);

  // Bind Open Folder buttons (Header, Sidebar Empty State, Welcome Screen)
  document.getElementById("btn-open-folder").onclick = () => handleOpenFolder();
  
  const btnSidebarOpen = document.getElementById("btn-sidebar-open-folder");
  if (btnSidebarOpen) btnSidebarOpen.onclick = () => handleOpenFolder();

  const btnWelcomeOpen = document.getElementById("btn-welcome-open-folder");
  if (btnWelcomeOpen) btnWelcomeOpen.onclick = () => handleOpenFolder();

  // Bind New File buttons (Sidebar, Welcome Screen)
  const btnSidebarNew = document.getElementById("btn-sidebar-new-file");
  if (btnSidebarNew) {
    btnSidebarNew.onclick = () => promptAndCreateFile();
  }

  const btnWelcomeNew = document.getElementById("btn-welcome-new-file");
  if (btnWelcomeNew) {
    btnWelcomeNew.onclick = () => promptAndCreateFile();
  }

  // Welcome Screen Quick Action Cards
  const btnWelcomeChat = document.getElementById("btn-welcome-chat");
  if (btnWelcomeChat) {
    btnWelcomeChat.onclick = () => {
      const tabChat = document.getElementById("tab-btn-chat");
      if (tabChat) tabChat.click();
      const chatInput = document.getElementById("chat-input");
      if (chatInput) chatInput.focus();
    };
  }

  const btnWelcomeTerm = document.getElementById("btn-welcome-terminal");
  if (btnWelcomeTerm) {
    btnWelcomeTerm.onclick = () => {
      const termDrawer = document.getElementById("workspace-terminal-drawer");
      if (termDrawer && termDrawer.style.display === "none") {
        const toggleBtn = document.getElementById("btn-toggle-terminal");
        if (toggleBtn) toggleBtn.click();
      } else {
        const termInput = document.getElementById("terminal-input");
        if (termInput) termInput.focus();
      }
    };
  }

  document.getElementById("btn-refresh-tree").onclick = () => refreshFileTree();
  document.getElementById("btn-save-file").onclick = () => window.codeEditor.saveActiveFile();
}

function promptAndCreateFile() {
  const filename = prompt("Enter file name (e.g. main.py, Solution.java, script.c, index.html):", "main.py");
  if (filename && filename.trim()) {
    window.codeEditor.openNewFile(filename.trim(), "");
  }
}

async function handleOpenFolder() {
  const res = await window.pywebview.api.pick_folder();
  if (res && res.success) {
    updateWorkspaceUI({
      has_folder: true,
      folder_name: res.name,
      root_path: res.path,
      terminal_cwd: res.terminal_cwd || res.path
    });
  }
}

function updateWorkspaceUI(info) {
  const folderBadgeText = document.getElementById("current-folder-name");
  const emptySidebar = document.getElementById("sidebar-empty-state");
  const treeContainer = document.getElementById("file-tree-container");

  if (info && info.has_folder) {
    folderBadgeText.innerText = info.folder_name;
    if (emptySidebar) emptySidebar.style.display = "none";
    if (treeContainer) treeContainer.style.display = "block";
    if (window.updateTerminalCwd && (info.terminal_cwd || info.root_path)) {
      window.updateTerminalCwd(info.terminal_cwd || info.root_path);
    }
    refreshFileTree();
  } else {
    folderBadgeText.innerText = "Select Folder";
    if (emptySidebar) emptySidebar.style.display = "block";
    if (treeContainer) {
      treeContainer.style.display = "none";
      treeContainer.innerHTML = "";
    }
  }
}

async function refreshFileTree() {
  const tree = await window.pywebview.api.get_file_tree();
  const container = document.getElementById("file-tree-container");
  container.innerHTML = "";

  if (!tree || tree.length === 0) {
    container.innerHTML = `<div style="padding:16px 12px; color:var(--text-muted); font-size:11px; text-align:center;">This folder is empty.<br><button class="btn" style="margin-top:8px; font-size:11px; padding:3px 8px;" onclick="promptAndCreateFile()">+ Create New File</button></div>`;
    return;
  }

  function renderTree(items, parentEl, depth = 0) {
    items.forEach(item => {
      const el = document.createElement("div");
      el.className = "tree-item";
      el.style.paddingLeft = `${14 + depth * 14}px`;

      let icon = "📄";
      if (item.is_dir) {
        icon = "📁";
      } else {
        const ext = (item.ext || "").toLowerCase();
        if (ext === ".py") icon = "🐍";
        else if (ext === ".c" || ext === ".h") icon = "⚙️";
        else if (ext === ".java") icon = "☕";
        else if (ext === ".json") icon = "📋";
        else if (ext === ".md") icon = "📝";
      }

      el.innerHTML = `<span>${icon}</span><span class="${item.is_dir ? 'tree-folder' : ''}">${item.name}</span>`;

      if (item.is_dir) {
        let expanded = false;
        const subContainer = document.createElement("div");
        subContainer.style.display = "none";

        el.onclick = () => {
          expanded = !expanded;
          subContainer.style.display = expanded ? "block" : "none";
          el.querySelector("span").innerText = expanded ? "📂" : "📁";
        };

        parentEl.appendChild(el);
        if (item.children && item.children.length > 0) {
          renderTree(item.children, subContainer, depth + 1);
        }
        parentEl.appendChild(subContainer);
      } else {
        el.onclick = () => {
          document.querySelectorAll(".tree-item").forEach(t => t.classList.remove("active"));
          el.classList.add("active");
          window.codeEditor.openFile(item.path);
        };
        parentEl.appendChild(el);
      }
    });
  }

  renderTree(tree, container);
}

function setupTerminal() {
  const pwshScreen = document.getElementById("pwsh-screen");
  const pwshHistory = document.getElementById("pwsh-history");
  const pwshPromptLabel = document.getElementById("pwsh-prompt-label");
  const termInput = document.getElementById("terminal-input");
  const termDrawer = document.getElementById("workspace-terminal-drawer");
  const resizerTerm = document.getElementById("resizer-terminal");
  const btnToggleTerm = document.getElementById("btn-toggle-terminal");
  const btnCloseTerm = document.getElementById("btn-close-term");
  const btnMaximizeTerm = document.getElementById("btn-maximize-term");

  let cmdHistory = [];
  let historyIdx = -1;
  let isMaximized = false;
  let isVisible = true;
  let currentCwd = "C:\\";

  const BANNER_HTML = '<div class="pwsh-banner">Windows PowerShell<br>Copyright (C) Microsoft Corporation. All rights reserved.<br><br></div>';

  function escapeHtml(text) {
    if (!text) return "";
    return text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  window.updateTerminalCwd = function(cwdPath) {
    if (!cwdPath) return;
    currentCwd = cwdPath;
    if (pwshPromptLabel) {
      pwshPromptLabel.innerText = `PS ${cwdPath}>`;
    }
  };

  if (pwshScreen) {
    pwshScreen.addEventListener("click", () => {
      if (termInput) termInput.focus();
    });
  }

  function toggleTerminal() {
    isVisible = !isVisible;
    termDrawer.style.display = isVisible ? "flex" : "none";
    if (resizerTerm) resizerTerm.style.display = isVisible ? "block" : "none";
    if (isVisible && termInput) termInput.focus();
    setTimeout(() => {
      if (window.codeEditor && window.codeEditor.layout) window.codeEditor.layout();
    }, 50);
  }

  if (btnToggleTerm) btnToggleTerm.onclick = () => toggleTerminal();
  if (btnCloseTerm) btnCloseTerm.onclick = () => toggleTerminal();

  if (btnMaximizeTerm) {
    btnMaximizeTerm.onclick = () => {
      isMaximized = !isMaximized;
      termDrawer.style.height = isMaximized ? "75%" : "220px";
      termDrawer.style.flex = isMaximized ? "0 0 75%" : "0 0 220px";
      btnMaximizeTerm.innerHTML = isMaximized ? "🗗" : "⛶";
      setTimeout(() => {
        if (window.codeEditor && window.codeEditor.layout) window.codeEditor.layout();
      }, 50);
    };
  }

  // Ctrl+` shortcut to toggle terminal like VS Code
  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && (e.key === "`" || e.code === "Backquote")) {
      e.preventDefault();
      toggleTerminal();
    }
  });

  function appendPwshOutput(cmd, res, executedAtCwd) {
    if (res && res.clear) {
      pwshHistory.innerHTML = BANNER_HTML;
      return;
    }

    const entry = document.createElement("div");
    entry.className = "pwsh-entry";

    const cmdLine = document.createElement("div");
    cmdLine.className = "pwsh-command-line";
    cmdLine.textContent = `PS ${executedAtCwd}> ${cmd}`;
    entry.appendChild(cmdLine);

    if (res.stdout) {
      const outLine = document.createElement("div");
      outLine.className = "pwsh-output";
      outLine.textContent = res.stdout;
      entry.appendChild(outLine);
    }

    if (res.stderr) {
      const errLine = document.createElement("div");
      errLine.className = "pwsh-output error";
      errLine.textContent = res.stderr;
      entry.appendChild(errLine);
    }

    pwshHistory.appendChild(entry);
    if (pwshScreen) {
      pwshScreen.scrollTop = pwshScreen.scrollHeight;
    }
  }

  async function executeCmd(cmd) {
    if (!cmd.trim()) return;
    cmdHistory.push(cmd);
    historyIdx = cmdHistory.length;
    const executedCwd = currentCwd;
    const res = await window.pywebview.api.run_terminal_command(cmd);
    appendPwshOutput(cmd, res, executedCwd);
    if (res && res.cwd) {
      window.updateTerminalCwd(res.cwd);
    }
  }

  termInput.onkeydown = async (e) => {
    if (e.key === "Enter") {
      const cmd = termInput.value;
      termInput.value = "";
      if (cmd.trim()) {
        await executeCmd(cmd.trim());
      } else {
        // Just print empty prompt line
        const entry = document.createElement("div");
        entry.className = "pwsh-entry";
        entry.innerHTML = `<div class="pwsh-command-line">PS ${currentCwd}&gt;</div>`;
        pwshHistory.appendChild(entry);
        if (pwshScreen) pwshScreen.scrollTop = pwshScreen.scrollHeight;
      }
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (cmdHistory.length > 0 && historyIdx > 0) {
        historyIdx--;
        termInput.value = cmdHistory[historyIdx] || "";
      }
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      if (historyIdx < cmdHistory.length - 1) {
        historyIdx++;
        termInput.value = cmdHistory[historyIdx] || "";
      } else {
        historyIdx = cmdHistory.length;
        termInput.value = "";
      }
    }
  };

  const btnClear = document.getElementById("btn-clear-term");
  if (btnClear) {
    btnClear.onclick = () => {
      pwshHistory.innerHTML = BANNER_HTML;
      if (termInput) termInput.focus();
    };
  }

  const btnGit = document.getElementById("btn-term-git");
  if (btnGit) btnGit.onclick = () => executeCmd("git status");

  const btnDir = document.getElementById("btn-term-dir");
  if (btnDir) btnDir.onclick = () => executeCmd("dir");

  const btnGcc = document.getElementById("btn-run-gcc");
  if (btnGcc) btnGcc.onclick = () => executeCmd("gcc --version");

  const btnJava = document.getElementById("btn-run-java");
  if (btnJava) {
    btnJava.onclick = async () => {
      if (window.codeEditor && window.codeEditor.activePath && window.codeEditor.activePath.endsWith(".java")) {
        const path = window.codeEditor.activePath;
        const name = path.replace(/\\/g, '/').split('/').pop().replace('.java', '');
        await executeCmd(`javac "${path}"; java "${name}"`);
      } else {
        await executeCmd("java -version");
      }
    };
  }

  const btnPython = document.getElementById("btn-run-python");
  if (btnPython) {
    btnPython.onclick = async () => {
      if (window.codeEditor && window.codeEditor.activePath) {
        await executeCmd(`python "${window.codeEditor.activePath}"`);
      } else {
        await executeCmd("python --version");
      }
    };
  }
}

function setupSearch() {
  const input = document.getElementById("global-search-input");
  const modal = document.getElementById("search-modal");
  const resultsContainer = document.getElementById("search-results-list");
  const closeBtn = document.getElementById("btn-close-search");

  closeBtn.onclick = () => modal.classList.remove("active");

  input.onkeydown = async (e) => {
    if (e.key === "Enter") {
      const query = input.value.trim();
      if (!query) return;

      resultsContainer.innerHTML = "<div style='color:var(--text-muted);'>Searching with Native C Core...</div>";
      modal.classList.add("active");

      const results = await window.pywebview.api.fast_search(query);
      resultsContainer.innerHTML = "";

      if (results.length === 0) {
        resultsContainer.innerHTML = `<div style='color:var(--text-muted);'>No matches found for '${query}'.</div>`;
        return;
      }

      results.forEach(m => {
        const item = document.createElement("div");
        item.style.padding = "6px 8px";
        item.style.borderBottom = "1px solid var(--border-color)";
        item.style.cursor = "pointer";
        item.innerHTML = `
          <div style="font-weight:600; color:var(--primary); font-size:12px;">${m.file}:${m.line}</div>
          <div style="font-family:var(--font-mono); font-size:11px; color:#c9d1d9;">${m.text}</div>
        `;
        item.onclick = () => {
          modal.classList.remove("active");
          window.codeEditor.openFile(m.file);
        };
        resultsContainer.appendChild(item);
      });
    }
  };
}

function setupSettings() {
  const modal = document.getElementById("settings-modal");
  const btnOpen = document.getElementById("btn-settings");
  const btnClose = document.getElementById("btn-close-settings");
  const btnSave = document.getElementById("btn-save-settings");
  const btnTest = document.getElementById("btn-test-nvidia");
  const apiKeyInput = document.getElementById("settings-api-key");
  const plannerSelect = document.getElementById("settings-planner-model");
  const coderSelect = document.getElementById("settings-coder-model");
  const testRes = document.getElementById("settings-test-result");

  btnOpen.onclick = async () => {
    const s = await window.pywebview.api.get_settings();
    if (s.has_api_key) {
      apiKeyInput.placeholder = `Configured (${s.api_key_masked})`;
    }
    plannerSelect.value = s.default_planner;
    coderSelect.value = s.default_coder;
    testRes.innerText = "";
    modal.classList.add("active");
  };

  btnClose.onclick = () => modal.classList.remove("active");

  btnTest.onclick = async () => {
    testRes.innerText = "Testing NVIDIA API endpoint...";
    const key = apiKeyInput.value.trim();
    if (key) {
      await window.pywebview.api.save_settings(key, plannerSelect.value, coderSelect.value);
    }
    const s = await window.pywebview.api.save_settings(key, plannerSelect.value, coderSelect.value);
    if (s.connection_test && s.connection_test.success) {
      testRes.innerHTML = `<span style="color:#57ab5a;">✓ Connected to NVIDIA NIM: ${s.connection_test.model}</span>`;
    } else {
      testRes.innerHTML = `<span style="color:#f85149;">✗ Error: ${(s.connection_test && s.connection_test.error) || 'Failed'}</span>`;
    }
  };

  btnSave.onclick = async () => {
    const key = apiKeyInput.value.trim();
    await window.pywebview.api.save_settings(key, plannerSelect.value, coderSelect.value);
    modal.classList.remove("active");
  };
}

function setupResizers() {
  function setIframePointer(enable) {
    document.querySelectorAll("iframe").forEach(f => {
      f.style.pointerEvents = enable ? "auto" : "none";
    });
  }

  // 1. Sidebar Resizer (Left horizontal drag)
  const resizerSidebar = document.getElementById("resizer-sidebar");
  const sidebar = document.getElementById("app-sidebar");
  if (resizerSidebar && sidebar) {
    let isDragging = false;
    let startX = 0;
    let startWidth = 0;

    resizerSidebar.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      e.stopPropagation();
      isDragging = true;
      startX = e.clientX;
      startWidth = sidebar.getBoundingClientRect().width;
      try { resizerSidebar.setPointerCapture(e.pointerId); } catch (_) {}
      resizerSidebar.classList.add("resizing");
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
      setIframePointer(false);
    });

    resizerSidebar.addEventListener("pointermove", (e) => {
      if (!isDragging) return;
      e.preventDefault();
      const dx = e.clientX - startX;
      let newWidth = Math.round(startWidth + dx);
      if (newWidth < 120) newWidth = 120;
      if (newWidth > 650) newWidth = 650;
      sidebar.style.width = `${newWidth}px`;
      sidebar.style.flex = `0 0 ${newWidth}px`;
      if (window.codeEditor && window.codeEditor.layout) window.codeEditor.layout();
    });

    const stopSidebarDrag = (e) => {
      if (isDragging) {
        isDragging = false;
        try { resizerSidebar.releasePointerCapture(e.pointerId); } catch (_) {}
        resizerSidebar.classList.remove("resizing");
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
        setIframePointer(true);
        if (window.codeEditor && window.codeEditor.layout) window.codeEditor.layout();
      }
    };
    resizerSidebar.addEventListener("pointerup", stopSidebarDrag);
    resizerSidebar.addEventListener("pointercancel", stopSidebarDrag);
  }

  // 2. Chat / Workforce Panel Resizer (Right horizontal drag)
  const resizerChat = document.getElementById("resizer-chat");
  const rightPanel = document.getElementById("app-right-panel");
  if (resizerChat && rightPanel) {
    let isDragging = false;
    let startX = 0;
    let startWidth = 0;

    resizerChat.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      e.stopPropagation();
      isDragging = true;
      startX = e.clientX;
      startWidth = rightPanel.getBoundingClientRect().width;
      try { resizerChat.setPointerCapture(e.pointerId); } catch (_) {}
      resizerChat.classList.add("resizing");
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
      setIframePointer(false);
    });

    resizerChat.addEventListener("pointermove", (e) => {
      if (!isDragging) return;
      e.preventDefault();
      const dx = startX - e.clientX;
      let newWidth = Math.round(startWidth + dx);
      if (newWidth < 220) newWidth = 220;
      if (newWidth > 850) newWidth = 850;
      rightPanel.style.width = `${newWidth}px`;
      rightPanel.style.flex = `0 0 ${newWidth}px`;
      if (window.codeEditor && window.codeEditor.layout) window.codeEditor.layout();
    });

    const stopChatDrag = (e) => {
      if (isDragging) {
        isDragging = false;
        try { resizerChat.releasePointerCapture(e.pointerId); } catch (_) {}
        resizerChat.classList.remove("resizing");
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
        setIframePointer(true);
        if (window.codeEditor && window.codeEditor.layout) window.codeEditor.layout();
      }
    };
    resizerChat.addEventListener("pointerup", stopChatDrag);
    resizerChat.addEventListener("pointercancel", stopChatDrag);
  }

  // 3. Terminal Drawer Resizer (Vertical drag)
  const resizerTerminal = document.getElementById("resizer-terminal");
  const terminalDrawer = document.getElementById("workspace-terminal-drawer");
  const mainStage = document.querySelector(".main-stage");
  if (resizerTerminal && terminalDrawer) {
    let isDragging = false;
    let startY = 0;
    let startHeight = 0;

    resizerTerminal.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      e.stopPropagation();
      isDragging = true;
      startY = e.clientY;
      startHeight = terminalDrawer.getBoundingClientRect().height;
      try { resizerTerminal.setPointerCapture(e.pointerId); } catch (_) {}
      resizerTerminal.classList.add("resizing");
      document.body.style.cursor = "row-resize";
      document.body.style.userSelect = "none";
      setIframePointer(false);
    });

    resizerTerminal.addEventListener("pointermove", (e) => {
      if (!isDragging) return;
      e.preventDefault();
      const dy = startY - e.clientY;
      let newHeight = Math.round(startHeight + dy);
      const stageHeight = mainStage ? mainStage.getBoundingClientRect().height : 600;
      const maxHeight = Math.floor(stageHeight * 0.85);
      if (newHeight < 40) newHeight = 40;
      if (newHeight > maxHeight) newHeight = maxHeight;
      terminalDrawer.style.height = `${newHeight}px`;
      terminalDrawer.style.flex = `0 0 ${newHeight}px`;
      if (window.codeEditor && window.codeEditor.layout) window.codeEditor.layout();
    });

    const stopTerminalDrag = (e) => {
      if (isDragging) {
        isDragging = false;
        try { resizerTerminal.releasePointerCapture(e.pointerId); } catch (_) {}
        resizerTerminal.classList.remove("resizing");
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
        setIframePointer(true);
        if (window.codeEditor && window.codeEditor.layout) window.codeEditor.layout();
      }
    };
    resizerTerminal.addEventListener("pointerup", stopTerminalDrag);
    resizerTerminal.addEventListener("pointercancel", stopTerminalDrag);
  }

  // Window resize relayout
  window.addEventListener("resize", () => {
    if (window.codeEditor && window.codeEditor.layout) window.codeEditor.layout();
  });
}

function setupPanelToggles() {
  // Toggle Sidebar Button
  const btnToggleSidebar = document.getElementById("btn-toggle-sidebar");
  const sidebarEl = document.getElementById("app-sidebar");
  const resizerSidebar = document.getElementById("resizer-sidebar");
  if (btnToggleSidebar && sidebarEl) {
    let sidebarVisible = true;
    btnToggleSidebar.onclick = () => {
      sidebarVisible = !sidebarVisible;
      sidebarEl.style.display = sidebarVisible ? "flex" : "none";
      if (resizerSidebar) resizerSidebar.style.display = sidebarVisible ? "block" : "none";
      btnToggleSidebar.style.opacity = sidebarVisible ? "1" : "0.5";
      if (window.codeEditor && window.codeEditor.layout) window.codeEditor.layout();
    };
  }

  // Toggle Chat & Copilot Panel Button
  const btnToggleChat = document.getElementById("btn-toggle-chat");
  const rightPanelEl = document.getElementById("app-right-panel");
  const resizerChat = document.getElementById("resizer-chat");
  if (btnToggleChat && rightPanelEl) {
    let chatVisible = true;
    btnToggleChat.onclick = () => {
      chatVisible = !chatVisible;
      rightPanelEl.style.display = chatVisible ? "flex" : "none";
      if (resizerChat) resizerChat.style.display = chatVisible ? "block" : "none";
      btnToggleChat.style.opacity = chatVisible ? "1" : "0.5";
      if (window.codeEditor && window.codeEditor.layout) window.codeEditor.layout();
    };
  }
}

