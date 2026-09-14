/* DemonTalk App - Perf-Optimized for Low-End Android WebView */
const App = {
  currentScreen: 'Radio',
  isTransmitting: false,
  isReceiving: false,
  currentChannel: null,
  deviceName: 'DemonTalk',
  peerCount: 0,
  batteryLevel: 100,

  // Interaction state
  _touchStartX: 0,
  _touchStartY: 0,
  _pullStartY: 0,
  _isPulling: false,
  _audioCtx: null,
  _vibrationEnabled: true,
  _prefersReducedMotion: false,

  // Cached DOM refs (avoids repeated getElementById)
  _dom: {},

  // Waveform state
  _waveformDirty: false,
  _PI_OVER_32: Math.PI / 32,

  init() {
    this._prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    this._cacheDom();
    this.bindNav();
    this.bindPTT();
    this.bindChat();
    this.bindDevices();
    this.bindChannels();
    this.bindSettings();
    this.bindEmergency();
    this.bindModal();
    this.initWaveforms();
    this.initSwipeGestures();
    this.initAudioContext();
    this.loadDeviceInfo();
    this.showToast('DemonTalk Ready');
  },

  // --- Cache DOM references once ---
  _cacheDom() {
    const ids = [
      'statusDot', 'statusText', 'peerCount', 'batteryPct', 'batteryInfo',
      'deviceName', 'channelName', 'chatChannelLabel',
      'pttBtn', 'pttIcon', 'pttLabel',
      'messageList', 'chatInput', 'sendBtn',
      'channelList', 'channelEmpty', 'createChannelBtn', 'channelName',
      'deviceList', 'deviceEmpty', 'scanBtn', 'scanStatus',
      'settingsList',
      'emergencyBtn',
      'modalOverlay', 'modalTitle', 'modalBody', 'modalActions',
      'toast', 'pullIndicator',
    ];
    for (let i = 0; i < ids.length; i++) {
      this._dom[ids[i]] = document.getElementById(ids[i]);
    }
  },

  // --- Audio Context for Sound Effects ---
  initAudioContext() {
    try {
      this._audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const resume = () => {
        if (this._audioCtx && this._audioCtx.state === 'suspended') this._audioCtx.resume();
      };
      document.addEventListener('touchstart', resume, { once: true });
      document.addEventListener('click', resume, { once: true });
    } catch (e) { /* AudioContext not available */ }
  },

  playTone(frequency, duration, type = 'sine', volume = 0.3) {
    if (!this._audioCtx) return;
    try {
      const osc = this._audioCtx.createOscillator();
      const gain = this._audioCtx.createGain();
      osc.connect(gain);
      gain.connect(this._audioCtx.destination);
      osc.type = type;
      osc.frequency.setValueAtTime(frequency, this._audioCtx.currentTime);
      gain.gain.setValueAtTime(volume, this._audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, this._audioCtx.currentTime + duration);
      osc.start();
      osc.stop(this._audioCtx.currentTime + duration);
    } catch (e) { /* silent */ }
  },

  playConnectSound() {
    this.playTone(523, 0.1, 'sine', 0.2);
    setTimeout(() => this.playTone(659, 0.1, 'sine', 0.2), 100);
    setTimeout(() => this.playTone(784, 0.15, 'sine', 0.25), 200);
  },
  playDisconnectSound() {
    this.playTone(784, 0.1, 'sine', 0.2);
    setTimeout(() => this.playTone(523, 0.15, 'sine', 0.2), 100);
  },
  playTXStartSound() { this.playTone(880, 0.08, 'square', 0.15); },
  playTXStopSound() { this.playTone(440, 0.12, 'square', 0.1); },
  playRXStartSound() { this.playTone(660, 0.06, 'sine', 0.15); },
  playErrorSound() { this.playTone(220, 0.2, 'sawtooth', 0.15); },
  playSuccessSound() {
    this.playTone(523, 0.08, 'sine', 0.2);
    setTimeout(() => this.playTone(784, 0.12, 'sine', 0.2), 80);
  },

  // --- Haptic Feedback ---
  vibrate(pattern) {
    if (!this._vibrationEnabled || !navigator.vibrate) return;
    try { navigator.vibrate(pattern); } catch (e) { /* silent */ }
  },

  // --- Ripple Effect (CSS animation, auto-cleanup) ---
  createRipple(element, event) {
    if (this._prefersReducedMotion) return;
    const ripple = document.createElement('span');
    ripple.className = 'ripple';
    const rect = element.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    let x, y;
    if (event.touches) {
      x = event.touches[0].clientX - rect.left - size / 2;
      y = event.touches[0].clientY - rect.top - size / 2;
    } else {
      x = (event.clientX || rect.left + rect.width / 2) - rect.left - size / 2;
      y = (event.clientY || rect.top + rect.height / 2) - rect.top - size / 2;
    }
    ripple.style.cssText = 'width:' + size + 'px;height:' + size + 'px;left:' + x + 'px;top:' + y + 'px';
    element.appendChild(ripple);
    ripple.addEventListener('animationend', function() { ripple.remove(); }, { once: true });
  },

  // --- Navigation ---
  bindNav() {
    const btns = this._dom.bottomNav ? this._dom.bottomNav.querySelectorAll('.nav-btn') : document.querySelectorAll('.nav-btn');
    for (let i = 0; i < btns.length; i++) {
      btns[i].addEventListener('click', (e) => {
        this.createRipple(btns[i], e);
        this.vibrate(10);
        this.switchScreen(btns[i].dataset.screen);
      });
    }
  },

  switchScreen(name) {
    if (name === this.currentScreen) return;
    const screens = document.querySelectorAll('.screen');
    const oldScreen = document.getElementById('screen' + this.currentScreen);
    const newScreen = document.getElementById('screen' + name);
    if (!newScreen) return;

    // Batch classList operations
    for (let i = 0; i < screens.length; i++) screens[i].classList.remove('active');
    const navBtns = this._dom.bottomNav ? this._dom.bottomNav.querySelectorAll('.nav-btn') : document.querySelectorAll('.nav-btn');
    for (let i = 0; i < navBtns.length; i++) navBtns[i].classList.remove('active');

    if (!this._prefersReducedMotion && oldScreen && newScreen) {
      const oldIndex = Array.from(screens).indexOf(oldScreen);
      const newIndex = Array.from(screens).indexOf(newScreen);
      const direction = newIndex > oldIndex ? 'left' : 'right';
      oldScreen.classList.add('screen-exit-' + direction);
      newScreen.classList.add('screen-enter-' + direction);
      setTimeout(() => {
        oldScreen.classList.remove('screen-exit-' + direction);
        newScreen.classList.remove('screen-enter-' + direction);
        newScreen.classList.add('active');
      }, 50);
    } else {
      newScreen.classList.add('active');
    }

    this.currentScreen = name;
    document.querySelector('[data-screen="' + name + '"]')?.classList.add('active');

    if (name === 'Devices') this.animateCards('#deviceList');
    if (name === 'Channels') this.animateCards('#channelList');
  },

  // --- Swipe Gestures (consolidated touchmove) ---
  initSwipeGestures() {
    const screens = ['Radio', 'Devices', 'Channels', 'Chat', 'Settings'];
    const swipeThreshold = 80;

    document.addEventListener('touchstart', (e) => {
      this._touchStartX = e.touches[0].clientX;
      this._touchStartY = e.touches[0].clientY;
    }, { passive: true });

    // Single consolidated touchmove listener
    document.addEventListener('touchmove', (e) => {
      const deltaY = e.touches[0].clientY - this._touchStartY;

      // Pull-to-refresh (only on Devices screen)
      if (this.currentScreen === 'Devices') {
        const deviceList = this._dom.deviceList || document.getElementById('deviceList');
        if (deviceList && deviceList.scrollTop === 0 && deltaY > 0) {
          this._isPulling = true;
          this._pullStartY = e.touches[0].clientY;
        }
        if (this._isPulling) {
          const pullDistance = e.touches[0].clientY - this._pullStartY;
          if (pullDistance > 10 && pullDistance < 150) {
            const indicator = this._dom.pullIndicator || document.getElementById('pullIndicator');
            if (indicator) {
              indicator.style.transform = 'translateY(' + (pullDistance - 40) + 'px)';
              indicator.classList.add('visible');
              const pullText = indicator.querySelector('.pull-text');
              if (pullText) pullText.textContent = pullDistance > 100 ? 'Release to refresh' : 'Pull to refresh';
            }
          }
        }
      }
    }, { passive: true });

    document.addEventListener('touchend', (e) => {
      // Swipe navigation
      const deltaX = e.changedTouches[0].clientX - this._touchStartX;
      const deltaY = e.changedTouches[0].clientY - this._touchStartY;
      if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > swipeThreshold) {
        const currentIndex = screens.indexOf(this.currentScreen);
        if (deltaX > 0 && currentIndex > 0) {
          this.vibrate(15);
          this.switchScreen(screens[currentIndex - 1]);
        } else if (deltaX < 0 && currentIndex < screens.length - 1) {
          this.vibrate(15);
          this.switchScreen(screens[currentIndex + 1]);
        }
      }

      // Pull-to-refresh release
      if (this._isPulling) {
        this._isPulling = false;
        const indicator = this._dom.pullIndicator || document.getElementById('pullIndicator');
        if (indicator) {
          const pullDistance = e.changedTouches[0].clientY - this._pullStartY;
          if (pullDistance > 100) {
            this.vibrate(20);
            this.scanDevices();
          }
          indicator.classList.remove('visible');
          indicator.style.transform = '';
        }
      }
    }, { passive: true });
  },

  // --- Card Entrance Animations (batched via rAF) ---
  animateCards(containerSelector) {
    if (this._prefersReducedMotion) return;
    const container = document.querySelector(containerSelector);
    if (!container) return;
    const cards = container.querySelectorAll('.card');
    requestAnimationFrame(() => {
      for (let i = 0; i < cards.length; i++) {
        cards[i].style.opacity = '0';
        cards[i].style.transform = 'translateY(20px)';
        cards[i].style.transition = 'opacity 0.3s ease-out, transform 0.3s ease-out';
      }
      requestAnimationFrame(() => {
        for (let i = 0; i < cards.length; i++) {
          cards[i].style.opacity = '1';
          cards[i].style.transform = 'translateY(0)';
        }
      });
    });
  },

  // --- PTT (instant visual feedback via .pressing) ---
  bindPTT() {
    const btn = this._dom.pttBtn || document.getElementById('pttBtn');
    let holdTimeout;
    let pressStartTime;

    const startTX = (e) => {
      e.preventDefault();
      if (this.isReceiving) {
        this.vibrate([30, 20, 30]);
        this.playErrorSound();
        return;
      }
      pressStartTime = Date.now();
      btn.classList.add('pressing');  // Instant visual feedback (<1ms)
      this.vibrate(15);
      clearTimeout(holdTimeout);
      holdTimeout = setTimeout(() => {
        this.startTransmitting();
      }, 50);
    };

    const stopTX = (e) => {
      e.preventDefault();
      btn.classList.remove('pressing');
      clearTimeout(holdTimeout);
      if (this.isTransmitting) {
        const pressDuration = Date.now() - pressStartTime;
        this.vibrate(pressDuration < 100 ? 8 : [10, 30, 10]);
        this.stopTransmitting();
      }
    };

    btn.addEventListener('mousedown', startTX);
    btn.addEventListener('mouseup', stopTX);
    btn.addEventListener('mouseleave', stopTX);
    btn.addEventListener('touchstart', startTX, { passive: false });
    btn.addEventListener('touchend', stopTX, { passive: false });
    btn.addEventListener('touchcancel', stopTX, { passive: false });
  },

  async startTransmitting() {
    this.isTransmitting = true;
    const btn = this._dom.pttBtn;
    btn.classList.add('tx');
    btn.classList.remove('rx', 'pressing');
    this._dom.pttLabel.textContent = 'TRANSMITTING';
    this._dom.pttIcon.textContent = 'stop';
    this._dom.statusDot.className = 'status-dot tx';
    this._dom.statusText.textContent = 'TRANSMITTING';
    this.vibrate(25);
    this.playTXStartSound();
    try { await Bridge.call('start_transmitting'); } catch (e) { console.log(e); }
  },

  async stopTransmitting() {
    this.isTransmitting = false;
    const btn = this._dom.pttBtn;
    btn.classList.remove('tx');
    this._dom.pttLabel.textContent = 'READY';
    this._dom.pttIcon.textContent = 'mic';
    this._dom.statusDot.className = 'status-dot online';
    this._dom.statusText.textContent = 'STANDBY';
    this.playTXStopSound();
    try { await Bridge.call('stop_transmitting'); } catch (e) { console.log(e); }
  },

  // --- Chat ---
  bindChat() {
    const input = this._dom.chatInput;
    const sendBtn = this._dom.sendBtn;
    const send = async () => {
      const text = input.value.trim();
      if (!text) return;
      const rect = sendBtn.getBoundingClientRect();
      this.createRipple(sendBtn, { clientX: rect.left + 24, clientY: rect.top + 24 });
      this.vibrate(10);
      this.addMessage(this.deviceName, text, true);
      input.value = '';
      this.playSuccessSound();
      try { await Bridge.call('send_text', text, this.currentChannel || ''); } catch (e) { console.log(e); }
    };
    sendBtn.addEventListener('click', send);
    input.addEventListener('keydown', (e) => { if (e.key === 'Enter') send(); });
  },

  addMessage(sender, text, own = false, time = '') {
    const list = this._dom.messageList;
    if (!time) {
      const now = new Date();
      time = (now.getHours() < 10 ? '0' : '') + now.getHours() + ':' + (now.getMinutes() < 10 ? '0' : '') + now.getMinutes();
    }
    const bubble = document.createElement('div');
    bubble.className = 'msg-bubble' + (own ? ' own' : '');
    bubble.innerHTML = '<div class="msg-sender">' + this.esc(sender) + '</div><div class="msg-text">' + this.esc(text) + '</div><div class="msg-time">' + time + '</div>';
    list.appendChild(bubble);
    list.scrollTop = list.scrollHeight;
  },

  // --- Channels ---
  bindChannels() {
    (this._dom.createChannelBtn || document.getElementById('createChannelBtn'))?.addEventListener('click', () => this.showCreateChannelModal());
  },

  async showCreateChannelModal() {
    this.showModal('Create Channel', [
      { id: 'chName', placeholder: 'Channel name', type: 'text' },
      { id: 'chPass', placeholder: 'Password (optional)', type: 'password' }
    ], [
      { label: 'Cancel', class: 'cancel', action: () => this.hideModal() },
      { label: 'Create', class: 'primary', action: async () => {
        const name = document.getElementById('chName')?.value.trim();
        if (!name) return;
        try {
          await Bridge.call('create_channel', name, document.getElementById('chPass')?.value || '');
          this.hideModal();
          this.loadChannels();
          this.playSuccessSound();
          this.showToast('Channel created');
        } catch (e) { console.log(e); }
      }}
    ]);
  },

  async loadChannels() {
    try {
      const channels = await Bridge.call('get_channels');
      const list = this._dom.channelList;
      const empty = this._dom.channelEmpty;
      // Clear via innerHTML (single reflow vs many removeChild)
      list.innerHTML = '';
      if (!channels || !channels.length) { empty.style.display = ''; return; }
      empty.style.display = 'none';
      // DocumentFragment for batch DOM insertion
      const frag = document.createDocumentFragment();
      for (let i = 0; i < channels.length; i++) {
        const ch = channels[i];
        const card = document.createElement('div');
        card.className = 'card' + (ch.id === this.currentChannel ? ' active' : '');
        card.innerHTML =
          '<div class="card-info"><div class="card-title">' + this.esc(ch.name) +
          '</div><div class="card-sub">' + (ch.member_count || 0) + ' members' +
          (ch.is_locked ? '  🔒' : '') + '</div></div>' +
          '<button class="card-action join">JOIN</button>';
        const joinBtn = card.querySelector('.card-action');
        joinBtn.addEventListener('click', async (e) => {
          e.stopPropagation();
          this.createRipple(card, e);
          this.vibrate(15);
          try { await Bridge.call('join_channel', ch.id); } catch (err) { console.log(err); }
          this.currentChannel = ch.id;
          this._dom.channelName.textContent = ch.name;
          this._dom.chatChannelLabel.textContent = ch.name;
          this.loadChannels();
          this.playConnectSound();
        });
        frag.appendChild(card);
      }
      list.appendChild(frag);  // Single DOM insertion
      this.animateCards('#channelList');
    } catch (e) { console.log(e); }
  },

  // --- Devices ---
  bindDevices() {
    (this._dom.scanBtn || document.getElementById('scanBtn'))?.addEventListener('click', (e) => {
      this.createRipple(document.getElementById('scanBtn'), e);
      this.vibrate(10);
      this.scanDevices();
    });
  },

  async scanDevices() {
    const scanBtn = this._dom.scanBtn;
    const scanStatus = this._dom.scanStatus;
    scanBtn.classList.add('loading');
    scanStatus.textContent = 'Scanning for devices...';
    this.vibrate(10);
    try { await Bridge.call('scan_devices'); } catch (e) { console.log(e); }
    setTimeout(() => { scanBtn.classList.remove('loading'); this.loadDevices(); }, 5000);
  },

  async loadDevices() {
    try {
      const devices = await Bridge.call('get_devices');
      const list = this._dom.deviceList;
      const empty = this._dom.deviceEmpty;
      list.innerHTML = '';
      if (!devices || !Object.keys(devices).length) { empty.style.display = ''; return; }
      empty.style.display = 'none';
      const frag = document.createDocumentFragment();
      const devArr = Object.values(devices);
      for (let i = 0; i < devArr.length; i++) {
        const dev = devArr[i];
        const online = dev.online;
        const card = document.createElement('div');
        card.className = 'card';
        card.innerHTML =
          '<div class="card-avatar ' + (online ? 'online' : 'offline') + '">' + ((dev.name || '?')[0].toUpperCase()) + '</div>' +
          '<div class="card-info"><div class="card-title">' + this.esc(dev.name) +
          '</div><div class="card-sub" style="color:' + (online ? 'var(--green)' : 'var(--text3)') + '">' +
          dev.ip + ' • ' + (online ? 'Online' : 'Offline') + '</div></div>' +
          (online ? '<button class="card-action connect">CONNECT</button>' : '');
        if (online) {
          const connectBtn = card.querySelector('.card-action');
          connectBtn?.addEventListener('click', async (e) => {
            e.stopPropagation();
            this.createRipple(card, e);
            this.vibrate(20);
            try {
              await Bridge.call('connect_device', dev.ip);
              this.playConnectSound();
              this.showToast('Connected to ' + dev.name);
            } catch (err) { this.playErrorSound(); console.log(err); }
          });
        }
        frag.appendChild(card);
      }
      list.appendChild(frag);
      scanStatus.textContent = 'Found ' + devArr.length + ' device(s)';
      this.animateCards('#deviceList');
    } catch (e) { console.log(e); }
  },

  // --- Settings ---
  bindSettings() { this.loadSettings(); },

  async loadSettings() {
    try {
      const settings = await Bridge.call('get_settings');
      const list = this._dom.settingsList;
      if (!settings) return;
      list.innerHTML = '';

      const sections = {
        'Device': [
          { key: 'device_name', label: 'Device Name', type: 'text', section: 'device' }
        ],
        'Audio': [
          { key: 'mic_sensitivity', label: 'Mic Sensitivity', type: 'range', section: 'audio' },
          { key: 'speaker_volume', label: 'Speaker Volume', type: 'range', section: 'audio' },
          { key: 'noise_suppression', label: 'Noise Suppression', type: 'toggle', section: 'audio' },
          { key: 'echo_cancellation', label: 'Echo Cancellation', type: 'toggle', section: 'audio' }
        ],
        'Network': [
          { key: 'auto_discovery', label: 'Auto Discovery', type: 'toggle', section: 'network' }
        ],
        'Notifications': [
          { key: 'connection_sounds', label: 'Connection Sounds', type: 'toggle', section: 'notifications' },
          { key: 'transmission_sound', label: 'TX Sound', type: 'toggle', section: 'notifications' },
          { key: 'receiving_sound', label: 'RX Sound', type: 'toggle', section: 'notifications' },
          { key: 'message_sound', label: 'Message Sound', type: 'toggle', section: 'notifications' },
          { key: 'vibration', label: 'Vibration', type: 'toggle', section: 'notifications' }
        ]
      };

      const frag = document.createDocumentFragment();
      const sectionEntries = Object.entries(sections);
      for (let s = 0; s < sectionEntries.length; s++) {
        const [sectionTitle, items] = sectionEntries[s];
        const sec = document.createElement('div');
        sec.className = 'settings-section';
        sec.innerHTML = '<div class="settings-section-title">' + sectionTitle.toUpperCase() + '</div>';
        for (let j = 0; j < items.length; j++) {
          const item = items[j];
          const val = this.getNested(settings, item.section, item.key);
          const row = document.createElement('div');
          row.className = 'settings-row';
          if (item.type === 'toggle') {
            row.innerHTML = '<span class="settings-label">' + item.label + '</span><label class="toggle"><input type="checkbox" ' + (val ? 'checked' : '') + ' data-section="' + item.section + '" data-key="' + item.key + '"><span class="toggle-track"></span></label>';
            row.querySelector('input').addEventListener('change', (e) => {
              this.vibrate(8);
              if (item.key === 'vibration') this._vibrationEnabled = e.target.checked;
              Bridge.call('set_setting', item.section, item.key, e.target.checked).catch(console.log);
            });
          } else if (item.type === 'range') {
            const pct = Math.round((val || 0.8) * 100);
            row.innerHTML = '<span class="settings-label">' + item.label + '</span><input type="range" class="range-slider" min="0" max="100" value="' + pct + '"><span class="settings-value">' + pct + '%</span>';
            const slider = row.querySelector('input');
            const valEl = row.querySelector('.settings-value');
            slider.addEventListener('input', (e) => { valEl.textContent = e.target.value + '%'; });
            slider.addEventListener('change', (e) => {
              this.vibrate(5);
              Bridge.call('set_setting', item.section, item.key, parseInt(e.target.value) / 100).catch(console.log);
            });
          } else if (item.type === 'text') {
            row.innerHTML = '<span class="settings-label">' + item.label + '</span><input class="modal-input" style="width:140px;margin:0" value="' + this.esc(String(val || '')) + '">';
            row.querySelector('input').addEventListener('change', (e) => {
              Bridge.call('set_setting', item.section, item.key, e.target.value.trim()).catch(console.log);
            });
          }
          sec.appendChild(row);
        }
        frag.appendChild(sec);
      }
      list.appendChild(frag);
      this.animateCards('#settingsList');
    } catch (e) { console.log(e); }
  },

  getNested(obj, ...keys) {
    return keys.reduce((o, k) => (o && o[k] !== undefined) ? o[k] : null, obj);
  },

  // --- Emergency ---
  bindEmergency() {
    (this._dom.emergencyBtn || document.getElementById('emergencyBtn'))?.addEventListener('click', (e) => {
      this.createRipple(document.getElementById('emergencyBtn'), e);
      this.vibrate([50, 50, 50, 50, 50]);
      this.showModal('Emergency Alert', [
        { id: 'emerMsg', placeholder: 'Emergency message (optional)', type: 'text' }
      ], [
        { label: 'Cancel', class: 'cancel', action: () => this.hideModal() },
        { label: 'SEND EMERGENCY', class: 'primary', action: async () => {
          const msg = document.getElementById('emerMsg')?.value || 'EMERGENCY';
          this.vibrate([100, 50, 100, 50, 100]);
          try { await Bridge.call('send_emergency', msg); } catch (e) { console.log(e); }
          this.hideModal();
          this.playErrorSound();
          this.showToast('EMERGENCY sent', true);
        }}
      ]);
    });
  },

  // --- Modal ---
  bindModal() {
    (this._dom.modalOverlay || document.getElementById('modalOverlay'))?.addEventListener('click', (e) => {
      if (e.target === e.currentTarget) this.hideModal();
    });
  },

  showModal(title, inputs, buttons) {
    const overlay = this._dom.modalOverlay;
    const body = this._dom.modalBody;
    const actions = this._dom.modalActions;
    this._dom.modalTitle.textContent = title;
    body.innerHTML = '';
    for (let i = 0; i < inputs.length; i++) {
      const inp = inputs[i];
      const el = document.createElement('input');
      el.className = 'modal-input';
      el.id = inp.id;
      el.placeholder = inp.placeholder || '';
      el.type = inp.type || 'text';
      body.appendChild(el);
    }
    actions.innerHTML = '';
    for (let i = 0; i < buttons.length; i++) {
      const btn = buttons[i];
      const el = document.createElement('button');
      el.className = 'modal-btn ' + (btn.class || '');
      el.textContent = btn.label;
      el.addEventListener('click', (e) => {
        this.createRipple(el, e);
        this.vibrate(10);
        btn.action();
      });
      actions.appendChild(el);
    }
    overlay.classList.add('show');
    setTimeout(() => body.querySelector('input')?.focus(), 100);
  },

  hideModal() {
    this._dom.modalOverlay.classList.remove('show');
  },

  // --- Waveforms (idle detection + pre-computed constants) ---
  initWaveforms() {
    this.txCanvas = document.getElementById('waveformTx');
    this.rxCanvas = document.getElementById('waveformRx');
    this.txCtx = this.txCanvas?.getContext('2d');
    this.rxCtx = this.rxCanvas?.getContext('2d');
    this.txLevels = new Float32Array(32);
    this.rxLevels = new Float32Array(32);
    this._animRunning = false;
    // Cache bound function to avoid per-frame allocation
    this._drawWaveformsBound = this._drawWaveforms.bind(this);
    // Polyfill roundRect for older WebViews
    if (this.txCtx && !this.txCtx.roundRect) {
      CanvasRenderingContext2D.prototype.roundRect = function(x, y, w, h, r) {
        const rad = typeof r === 'number' ? r : (r?.[0] || 0);
        this.beginPath();
        this.moveTo(x + rad, y);
        this.lineTo(x + w - rad, y);
        this.arcTo(x + w, y, x + w, y + rad, rad);
        this.lineTo(x + w, y + h - rad);
        this.arcTo(x + w, y + h, x + w - rad, y + h, rad);
        this.lineTo(x + rad, y + h);
        this.arcTo(x, y + h, x, y + h - rad, rad);
        this.lineTo(x, y + rad);
        this.arcTo(x, y, x + rad, y, rad);
        this.closePath();
      };
    }
    this._startWaveformLoop();
  },

  _startWaveformLoop() {
    if (this._animRunning) return;
    this._animRunning = true;
    this._animFrame = requestAnimationFrame(this._drawWaveformsBound);
  },

  _drawWaveforms() {
    this._drawWave(this.txCtx, this.txCanvas, this.txLevels, '#b44aff', '#ff1744', this.isTransmitting);
    this._drawWave(this.rxCtx, this.rxCanvas, this.rxLevels, '#00b0ff', '#00b0ff', this.isReceiving);

    // Decay levels
    let anyActive = false;
    for (let i = 0; i < 32; i++) {
      this.txLevels[i] *= 0.88;
      this.rxLevels[i] *= 0.88;
      if (this.txLevels[i] > 0.01 || this.rxLevels[i] > 0.01) anyActive = true;
    }

    // Idle detection: stop loop when waveforms fully decayed
    if (anyActive || this.isTransmitting || this.isReceiving || this._waveformDirty) {
      this._waveformDirty = false;
      this._animFrame = requestAnimationFrame(this._drawWaveformsBound);
    } else {
      this._animRunning = false;
    }
  },

  _drawWave(ctx, canvas, levels, color1, color2, active) {
    if (!ctx || !canvas) return;
    const w = canvas.width, h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    const barW = Math.max(2, (w - 31) / 32);
    for (let i = 0; i < 32; i++) {
      const level = levels[i];
      const barH = Math.max(3, level * h * 0.9);
      const x = i * (barW + 1);
      const y = (h - barH) / 2;
      ctx.globalAlpha = active ? (0.5 + level * 0.5) : 0.3;
      ctx.fillStyle = level > 0.2 ? color2 : color1;
      ctx.beginPath();
      ctx.roundRect(x, y, barW, barH, barW / 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  },

  setTxLevel(level) {
    for (let i = 0; i < 32; i++) {
      const target = level * (0.5 + 0.5 * Math.sin(i * this._PI_OVER_32));
      this.txLevels[i] = Math.max(target, this.txLevels[i] * 0.7);
    }
    this._waveformDirty = true;
    this._startWaveformLoop();
  },

  setRxLevel(level) {
    for (let i = 0; i < 32; i++) {
      const target = level * (0.5 + 0.5 * Math.sin(i * this._PI_OVER_32));
      this.rxLevels[i] = Math.max(target, this.rxLevels[i] * 0.7);
    }
    this._waveformDirty = true;
    this._startWaveformLoop();
  },

  // --- Device Info ---
  async loadDeviceInfo() {
    try {
      const info = await Bridge.call('get_device_info');
      if (info) {
        this.deviceName = info.name || 'DemonTalk';
        this._dom.deviceName.textContent = this.deviceName;
        this.batteryLevel = info.battery || 100;
        this._dom.batteryPct.textContent = this.batteryLevel + '%';
        this._dom.batteryInfo.textContent = this.batteryLevel + '%';
      }
    } catch (e) { console.log(e); }
  },

  // --- Event Handler (from Python) ---
  onEvent(event, data) {
    switch (event) {
      case 'state_changed':
        this.updateState(data.state);
        break;
      case 'voice_received':
        this.isReceiving = true;
        if (!this.isTransmitting) {
          this._dom.pttBtn.classList.add('rx');
          this._dom.pttLabel.textContent = 'RECEIVING';
          this._dom.statusDot.className = 'status-dot rx';
          this._dom.statusText.textContent = 'RECEIVING';
          this.playRXStartSound();
          this.vibrate(15);
        }
        clearTimeout(this._rxTimeout);
        this._rxTimeout = setTimeout(() => {
          this.isReceiving = false;
          this._dom.pttBtn.classList.remove('rx');
          if (!this.isTransmitting) {
            this._dom.pttLabel.textContent = 'READY';
            this._dom.statusDot.className = 'status-dot online';
            this._dom.statusText.textContent = 'STANDBY';
          }
        }, 800);
        break;
      case 'audio_level':
        this.setTxLevel(data.level || 0);
        break;
      case 'receive_level':
        this.setRxLevel(data.level || 0);
        break;
      case 'message_received':
        this.addMessage(data.sender_name || 'Unknown', data.message || '', false);
        this.vibrate(10);
        this.playSuccessSound();
        break;
      case 'device_found':
        this.loadDevices();
        break;
      case 'peer_connected':
        this.playConnectSound();
        this.vibrate([10, 30, 10]);
        this.peerCount = data.count || 0;
        this._dom.peerCount.textContent = this.peerCount + ' peers';
        break;
      case 'peer_disconnected':
        this.playDisconnectSound();
        this.peerCount = data.count || 0;
        this._dom.peerCount.textContent = this.peerCount + ' peers';
        break;
      case 'emergency':
        this.vibrate([200, 100, 200, 100, 200]);
        this.playErrorSound();
        this.showToast('EMERGENCY from ' + (data.sender_name || 'Unknown') + ': ' + (data.message || ''), true);
        break;
      case 'toast':
        this.showToast(data.message || '');
        break;
    }
  },

  updateState(state) {
    const map = {
      ready: ['online', 'STANDBY'],
      connected: ['online', 'CONNECTED'],
      transmitting: ['tx', 'TRANSMITTING'],
      receiving: ['rx', 'RECEIVING'],
      offline: ['', 'OFFLINE']
    };
    const [cls, label] = map[state] || ['', 'UNKNOWN'];
    this._dom.statusDot.className = 'status-dot ' + cls;
    this._dom.statusText.textContent = label;
  },

  // --- Toast ---
  showToast(msg, emergency = false) {
    const toast = this._dom.toast;
    toast.textContent = msg;
    toast.className = 'toast show' + (emergency ? ' emergency' : '');
    if (emergency) this.vibrate([100, 50, 100]);
    clearTimeout(this._toastTimeout);
    this._toastTimeout = setTimeout(() => { toast.className = 'toast'; }, 3000);
  },

  // --- Lightweight HTML escape (no DOM element creation) ---
  esc(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
};

window.App = App;
document.addEventListener('DOMContentLoaded', () => App.init());
