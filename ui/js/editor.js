/**
 * DOT AI Code Editor - Monaco Editor Integration & Tab Manager
 */
class CodeEditor {
  constructor() {
    this.monacoInstance = null;
    this.openTabs = new Map(); // path -> { path, content, isDirty, model }
    this.activePath = null;
    this.isMonacoLoaded = false;
    this.initMonaco();
    this.updateEditorVisibility();
  }

  initMonaco() {
    const fallback = document.getElementById("editor-fallback");
    if (typeof require !== "undefined") {
      try {
        require.config({ paths: { vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs' } });
        require(['vs/editor/editor.main'], () => {
          this.isMonacoLoaded = true;
          this.monacoInstance = monaco.editor.create(document.getElementById("monaco-editor"), {
            value: "// Welcome to DOT AI Autonomous Code Editor",
            language: "python",
            theme: "vs-dark",
            automaticLayout: true,
            fontSize: 13,
            minimap: { enabled: true },
            scrollBeyondLastLine: false,
            padding: { top: 8, bottom: 8 },
            lineNumbersMinChars: 3
          });

          this.updateEditorVisibility();

          // Ctrl+S listener
          this.monacoInstance.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
            this.saveActiveFile();
          });

          // Track changes
          this.monacoInstance.onDidChangeModelContent(() => {
            if (this.activePath && this.openTabs.has(this.activePath)) {
              const tab = this.openTabs.get(this.activePath);
              tab.content = this.monacoInstance.getValue();
              tab.isDirty = true;
              this.renderTabs();
            }
          });
        });
      } catch (e) {
        console.warn("Monaco loader error, using fallback textarea", e);
        fallback.style.display = "block";
      }
    } else {
      fallback.style.display = "block";
    }
  }

  getLanguageFromPath(path) {
    const ext = path.split('.').pop().toLowerCase();
    const map = {
      c: 'c', h: 'c', cpp: 'cpp', hpp: 'cpp',
      py: 'python',
      java: 'java',
      js: 'javascript', ts: 'typescript',
      json: 'json', md: 'markdown',
      html: 'html', css: 'css',
      bat: 'bat', sh: 'shell'
    };
    return map[ext] || 'plaintext';
  }

  async openFile(path) {
    if (this.openTabs.has(path)) {
      this.switchTab(path);
      return;
    }

    if (!window.pywebview || !window.pywebview.api) return;
    const res = await window.pywebview.api.read_file(path);
    if (!res.success) {
      alert("Failed to open file: " + res.error);
      return;
    }

    const content = res.content || "";
    const lang = this.getLanguageFromPath(path);

    let model = null;
    if (this.isMonacoLoaded && window.monaco) {
      model = monaco.editor.createModel(content, lang);
    }

    this.openTabs.set(path, {
      path: path,
      name: path.split('/').pop(),
      content: content,
      isDirty: false,
      model: model,
      lang: lang
    });

    this.switchTab(path);
  }

  openNewFile(filename = "untitled.py", initialContent = "") {
    let count = 1;
    let name = filename.trim() || "untitled.py";
    while (this.openTabs.has(name)) {
      name = `untitled_${count}.py`;
      count++;
    }
    const lang = this.getLanguageFromPath(name);
    let model = null;
    if (this.isMonacoLoaded && window.monaco) {
      model = monaco.editor.createModel(initialContent, lang);
    }
    this.openTabs.set(name, {
      path: name,
      name: name,
      content: initialContent,
      isDirty: true,
      model: model,
      lang: lang
    });
    this.switchTab(name);
  }

  updateEditorVisibility() {
    const welcome = document.getElementById("welcome-screen");
    const editorWrapper = document.getElementById("editor-wrapper");
    const hasFiles = this.openTabs.size > 0 && this.activePath !== null;

    if (hasFiles) {
      if (welcome) welcome.style.display = "none";
      if (editorWrapper) editorWrapper.style.display = "block";
      this.layout();
    } else {
      if (welcome) welcome.style.display = "flex";
      if (editorWrapper) editorWrapper.style.display = "none";
    }
  }

  switchTab(path) {
    if (!this.openTabs.has(path)) {
      this.updateEditorVisibility();
      return;
    }
    this.activePath = path;
    const tab = this.openTabs.get(path);

    if (this.isMonacoLoaded && this.monacoInstance) {
      if (tab.model) {
        this.monacoInstance.setModel(tab.model);
      } else {
        this.monacoInstance.setValue(tab.content);
        monaco.editor.setModelLanguage(this.monacoInstance.getModel(), tab.lang);
      }
    } else {
      const fallback = document.getElementById("editor-fallback");
      fallback.value = tab.content;
    }

    this.renderTabs();
    this.updateEditorVisibility();
    if (window.chatController) window.chatController.updateActiveFileBadge(path);
  }

  closeTab(path, event) {
    if (event) event.stopPropagation();
    if (!this.openTabs.has(path)) return;

    const tab = this.openTabs.get(path);
    if (tab.model) tab.model.dispose();
    this.openTabs.delete(path);

    if (this.activePath === path) {
      const remaining = Array.from(this.openTabs.keys());
      if (remaining.length > 0) {
        this.switchTab(remaining[remaining.length - 1]);
      } else {
        this.activePath = null;
        if (window.chatController) window.chatController.updateActiveFileBadge(null);
        if (this.isMonacoLoaded && this.monacoInstance) {
          this.monacoInstance.setValue("// No file open");
        }
      }
    }
    this.renderTabs();
    this.updateEditorVisibility();
  }

  async saveActiveFile() {
    if (!this.activePath) return;
    const tab = this.openTabs.get(this.activePath);
    if (!tab) return;

    let content = tab.content;
    if (this.isMonacoLoaded && this.monacoInstance) {
      content = this.monacoInstance.getValue();
    } else {
      content = document.getElementById("editor-fallback").value;
    }

    if (window.pywebview && window.pywebview.api) {
      const res = await window.pywebview.api.write_file(this.activePath, content);
      if (res.success) {
        tab.isDirty = false;
        this.renderTabs();
      } else {
        alert("Error saving: " + res.error);
      }
    }
  }

  renderTabs() {
    const container = document.getElementById("tab-bar");
    container.innerHTML = "";

    this.openTabs.forEach((tab, path) => {
      const tabEl = document.createElement("div");
      tabEl.className = `tab ${path === this.activePath ? 'active' : ''}`;
      tabEl.innerHTML = `
        <span>${tab.name} ${tab.isDirty ? '•' : ''}</span>
        <span class="tab-close" title="Close">✕</span>
      `;
      tabEl.onclick = () => this.switchTab(path);
      tabEl.querySelector(".tab-close").onclick = (e) => this.closeTab(path, e);
      container.appendChild(tabEl);
    });
  }

  layout() {
    if (this.isMonacoLoaded && this.monacoInstance) {
      this.monacoInstance.layout();
    }
  }
}

window.codeEditor = new CodeEditor();
