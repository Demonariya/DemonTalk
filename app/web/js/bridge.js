/* Python <-> JS Bridge for Kivy WebView */
const Bridge = {
  _pending: {},
  _id: 0,

  call(method, ...args) {
    return new Promise((resolve, reject) => {
      const id = ++this._id;
      this._pending[id] = { resolve, reject };
      const payload = JSON.stringify({ id, method, args });
      if (window.pyBridge) {
        window.pyBridge.call(payload);
      } else {
        // Desktop testing fallback
        console.log('[Bridge]', method, args);
        setTimeout(() => {
          this._onResponse(id, JSON.stringify({ ok: true, data: null }));
        }, 10);
      }
    });
  },

  // Called from Python
  _onResponse(id, json) {
    try {
      const { ok, data, error } = JSON.parse(json);
      const p = this._pending[id];
      if (p) {
        delete this._pending[id];
        ok ? p.resolve(data) : p.reject(error);
      }
    } catch (e) {
      console.error('Bridge response error:', e);
    }
  },

  // Called from Python to push events
  _onEvent(event, json) {
    try {
      const data = JSON.parse(json);
      window.App && App.onEvent(event, data);
    } catch (e) {
      console.error('Bridge event error:', e);
    }
  }
};

// Expose globally for Kivy WebView
window.Bridge = Bridge;
