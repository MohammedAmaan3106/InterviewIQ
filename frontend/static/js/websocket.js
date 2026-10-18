/**
 * InterviewIQ WebSocket Client Module.
 * Manages bidirectional real-time communication between browser and Python backend.
 */
class InterviewWebSocket {
  constructor() {
    this.ws = null;
    this.listeners = new Map();
    this.isConnected = false;
    this.reconnectAttempts = 0;
  }

  connect(timeoutMs = 6000) {
    return new Promise((resolve, reject) => {
      let settled = false;
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/interview`;

      const timer = setTimeout(() => {
        if (!settled) {
          settled = true;
          if (this.ws) {
            try { this.ws.close(); } catch (e) {}
          }
          reject(new Error('WebSocket connection timed out after 6 seconds'));
        }
      }, timeoutMs);

      try {
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
          if (!settled) {
            settled = true;
            clearTimeout(timer);
            this.isConnected = true;
            this.reconnectAttempts = 0;
            this.emit('connected', {});
            resolve();
          }
        };

        this.ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            if (message.type) {
              this.emit(message.type, message.data || message.report || message);
            }
          } catch (err) {
            console.error('Error parsing WebSocket message:', err);
          }
        };

        this.ws.onerror = (err) => {
          this.emit('error', err);
          if (!settled) {
            settled = true;
            clearTimeout(timer);
            reject(new Error('Could not establish WebSocket connection to server'));
          }
        };

        this.ws.onclose = () => {
          this.isConnected = false;
          this.emit('disconnected', {});
          if (!settled) {
            settled = true;
            clearTimeout(timer);
            reject(new Error('WebSocket closed before session handshake completed'));
          }
        };
      } catch (e) {
        if (!settled) {
          settled = true;
          clearTimeout(timer);
          reject(e);
        }
      }
    });
  }

  send(type, payload = {}) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, ...payload }));
    }
  }

  on(eventName, callback) {
    if (!this.listeners.has(eventName)) {
      this.listeners.set(eventName, []);
    }
    this.listeners.get(eventName).push(callback);
  }

  off(eventName, callback) {
    if (this.listeners.has(eventName)) {
      const list = this.listeners.get(eventName).filter(cb => cb !== callback);
      this.listeners.set(eventName, list);
    }
  }

  emit(eventName, data) {
    if (this.listeners.has(eventName)) {
      for (const cb of this.listeners.get(eventName)) {
        try {
          cb(data);
        } catch (err) {
          console.error(`Error in event listener for ${eventName}:`, err);
        }
      }
    }
  }

  disconnect() {
    if (this.ws) {
      try { this.ws.close(); } catch (e) {}
      this.ws = null;
      this.isConnected = false;
    }
  }
}

window.InterviewWebSocket = InterviewWebSocket;
