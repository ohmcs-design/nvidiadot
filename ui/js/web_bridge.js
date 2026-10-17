/**
 * DOT AI - Web & Docker Bridge Polyfill
 * When running in Docker / Web Browser mode (without pywebview desktop runtime),
 * this polyfills window.pywebview.api and streams server events via Server-Sent Events (SSE).
 */
(function() {
  if (window.pywebview && window.pywebview.api) {
    // Native pywebview already provided by desktop runtime
    return;
  }

  // Create API Proxy
  const apiProxy = new Proxy({}, {
    get(target, prop) {
      return async function(...args) {
        try {
          const response = await fetch('/api/call', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ method: prop, args: args })
          });
          const data = await response.json();
          if (data && data.__dot_api_response !== undefined) {
            return data.result;
          }
          return data;
        } catch (err) {
          console.error(`[WebBridge Error calling ${String(prop)}]:`, err);
          return { success: false, error: String(err) };
        }
      };
    }
  });

  window.pywebview = {
    api: apiProxy
  };

  // Connect to SSE stream for real-time events
  function connectEventStream() {
    const eventSource = new EventSource('/api/events');

    eventSource.onmessage = function(e) {
      try {
        const msg = JSON.parse(e.data);
        if (msg.event_type === 'chat' && window.onChatEvent) {
          window.onChatEvent(msg.data);
        } else if (msg.event_type === 'dot' && window.onDotEvent) {
          window.onDotEvent(msg.data);
        }
      } catch (err) {
        console.error('[WebBridge Event Parse Error]:', err);
      }
    };

    eventSource.onerror = function() {
      eventSource.close();
      // Reconnect after 2 seconds
      setTimeout(connectEventStream, 2000);
    };
  }

  connectEventStream();

  // Dispatch pywebviewready event for app.js initialization
  if (document.readyState === 'complete' || document.readyState === 'interactive') {
    setTimeout(() => window.dispatchEvent(new Event('pywebviewready')), 20);
  } else {
    document.addEventListener('DOMContentLoaded', () => {
      setTimeout(() => window.dispatchEvent(new Event('pywebviewready')), 20);
    });
  }
})();
