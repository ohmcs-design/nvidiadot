/**
 * DOT AI - Live In-App Browser & Multi-Page Web Inspector
 * Provides live preview, local server hosting, and deep site inspection with Nemotron 3.5.
 */
class LiveBrowser {
  constructor() {
    this.isBrowserOpen = false;
    this.isMobileView = false;
    this.localServerUrl = null;

    this.init();
  }

  init() {
    this.setupToggle();
    this.setupNavigation();
    this.setupLocalServer();
    this.setupInspection();
    this.setupMobileToggle();
  }

  setupToggle() {
    const toggleBtn = document.getElementById("btn-toggle-browser-tab");
    const editorWrapper = document.getElementById("editor-wrapper");
    const browserContainer = document.getElementById("web-preview-container");

    toggleBtn.onclick = () => {
      this.isBrowserOpen = !this.isBrowserOpen;
      if (this.isBrowserOpen) {
        editorWrapper.style.display = "none";
        browserContainer.style.display = "flex";
        toggleBtn.innerHTML = "📝 Back to Code Editor";
        toggleBtn.className = "btn btn-primary";

        // Auto load local server if not loaded yet
        if (!this.localServerUrl) {
          this.startLocalServer();
        }
      } else {
        browserContainer.style.display = "none";
        editorWrapper.style.display = "block";
        toggleBtn.innerHTML = "🌐 Live Web Browser & Inspector";
        toggleBtn.className = "btn btn-nvidia";
      }
    };
  }

  setupNavigation() {
    const urlInput = document.getElementById("browser-url-input");
    const goBtn = document.getElementById("btn-browser-go");
    const backBtn = document.getElementById("btn-browser-back");
    const fwdBtn = document.getElementById("btn-browser-forward");
    const refreshBtn = document.getElementById("btn-browser-refresh");
    const frame = document.getElementById("live-browser-frame");

    const navigateTo = (url) => {
      let target = url.trim();
      if (!target.startsWith("http://") && !target.startsWith("https://") && !target.startsWith("file://")) {
        target = "https://" + target;
      }
      urlInput.value = target;
      frame.src = target;
    };

    goBtn.onclick = () => navigateTo(urlInput.value);
    urlInput.onkeydown = (e) => {
      if (e.key === "Enter") navigateTo(urlInput.value);
    };

    backBtn.onclick = () => {
      try { frame.contentWindow.history.back(); } catch (e) {}
    };

    fwdBtn.onclick = () => {
      try { frame.contentWindow.history.forward(); } catch (e) {}
    };

    refreshBtn.onclick = () => {
      frame.src = frame.src;
    };
  }

  setupLocalServer() {
    const serverBtn = document.getElementById("btn-start-local-server");
    serverBtn.onclick = () => this.startLocalServer();
  }

  async startLocalServer() {
    const urlInput = document.getElementById("browser-url-input");
    const frame = document.getElementById("live-browser-frame");
    const serverBtn = document.getElementById("btn-start-local-server");

    serverBtn.innerText = "Starting...";

    if (window.pywebview && window.pywebview.api) {
      try {
        const res = await window.pywebview.api.start_preview_server();
        if (res.success && res.url) {
          this.localServerUrl = res.url;
          const targetUrl = `${res.url}/index.html`;
          urlInput.value = targetUrl;
          frame.src = targetUrl;
          serverBtn.innerText = "✓ Server Active";
          serverBtn.className = "btn btn-accent";
        }
      } catch (e) {
        alert("Failed to start preview server: " + e);
        serverBtn.innerText = "🚀 Run Local Server";
      }
    }
  }

  setupInspection() {
    const inspectBtn = document.getElementById("btn-browser-inspect-nemotron");
    const urlInput = document.getElementById("browser-url-input");

    inspectBtn.onclick = async () => {
      const url = urlInput.value.trim();
      if (!url) return;

      // Switch to Chat tab
      const btnChat = document.getElementById("tab-btn-chat");
      const btnGoals = document.getElementById("tab-btn-goals");
      const viewChat = document.getElementById("view-chat");
      const viewGoals = document.getElementById("view-goals");

      btnChat.className = "btn btn-primary";
      btnGoals.className = "btn";
      viewChat.style.display = "flex";
      viewGoals.style.display = "none";

      // Put prompt in chat
      const chatInput = document.getElementById("chat-input");
      chatInput.value = `Please inspect the website at ${url} across multiple pages. Analyze its navigation structure, headings, page content, and correlate it with our local files to see what is missing or broken.`;
      
      // Auto send
      if (window.chatController) {
        window.chatController.sendMessage();
      }
    };
  }

  setupMobileToggle() {
    const mobileBtn = document.getElementById("btn-toggle-mobile");
    const frame = document.getElementById("live-browser-frame");

    mobileBtn.onclick = () => {
      this.isMobileView = !this.isMobileView;
      if (this.isMobileView) {
        frame.style.width = "375px";
        frame.style.height = "667px";
        frame.style.boxShadow = "0 0 20px rgba(0,0,0,0.8)";
        frame.style.borderRadius = "20px";
        frame.style.border = "8px solid #2d333b";
        mobileBtn.innerText = "🖥️ Desktop";
      } else {
        frame.style.width = "100%";
        frame.style.height = "100%";
        frame.style.boxShadow = "none";
        frame.style.borderRadius = "0";
        frame.style.border = "none";
        mobileBtn.innerText = "📱 Mobile";
      }
    };
  }
}

window.liveBrowser = new LiveBrowser();
