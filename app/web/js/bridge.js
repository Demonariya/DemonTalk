/* Python <-> JS Bridge for Kivy WebView */
const Bridge = {
  _pending: {},
  _id: 0,

  call(method, ...args) {
    return new Promise((resolve, reject) => {
      const id = ++this._id;
      const timer = setTimeout(() => {
        if (this._pending[id]) {
          delete this._pending[id];
          reject(new Error(`Bridge timeout: ${method}`));
        }
      }, 15000);
      this._pending[id] = { resolve, reject, timer };
      const payload = JSON.stringify({ id, method, args });
      if (window.pyBridge) {
        window.pyBridge.call(payload);
      } else {
        // Desktop testing fallback
        console.log('[Bridge]', method, args);
        setTimeout(() => {
          this._onResponse(id, JSON.stringify({ ok: true, data: this._mockData(method, args) }));
        }, 10);
      }
    });
  },

  _mockData(method, args) {
    switch (method) {
      case 'get_device_info': return { name: 'Desktop User', id: 'desktop01', battery: 85 };
      case 'get_channels': return [];
      case 'get_devices': return {};
      case 'get_settings': return { device_name: 'Desktop User', audio: { mic_sensitivity: 0.8, speaker_volume: 0.8, noise_suppression: true, echo_cancellation: true }, network: { auto_discovery: true }, notifications: { connection_sounds: true, transmission_sound: true, receiving_sound: true, message_sound: true, vibration: true } };
      default: return null;
    }
  },

  // Called from Python
  _onResponse(id, json) {
    try {
      const { ok, data, error } = JSON.parse(json);
      const p = this._pending[id];
      if (p) {
        clearTimeout(p.timer);
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
      const data = typeof json === 'string' ? JSON.parse(json) : json;
      window.App && App.onEvent(event, data);
    } catch (e) {
      console.error('Bridge event error:', e);
    }
  }
};

// Expose globally for Kivy WebView
window.Bridge = Bridge;
