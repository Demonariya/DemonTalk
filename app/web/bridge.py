"""Python <-> JavaScript bridge for WebView."""
import json
from app.services.connection_service import ConnectionService
from app.config import AppConfig
from app.utils.logger import setup_logger

log = setup_logger('WebBridge')


class WebBridge:
    def __init__(self, webview):
        self.webview = webview
        self.service = ConnectionService()
        self.config = AppConfig()
        self._connect_events()

    def _connect_events(self):
        self.service.on('voice_received', lambda sid, sn, ad: self._push('voice_received', {'sender_id': sid, 'sender_name': sn}))
        self.service.on('audio_level', lambda lvl: self._push('audio_level', {'level': lvl}))
        self.service.on('receive_level', lambda lvl: self._push('receive_level', {'level': lvl}))
        self.service.on('message_received', lambda sid, sn, msg, ch: self._push('message_received', {'sender_id': sid, 'sender_name': sn, 'message': msg, 'channel_id': ch}))
        self.service.on('device_found', lambda did, name, ip, info: self._push('device_found', {'device_id': did, 'name': name, 'ip': ip}))
        self.service.on('peer_connected', lambda ip, port: self._push('peer_connected', {'ip': ip, 'port': port}))
        self.service.on('peer_disconnected', lambda pid: self._push('peer_disconnected', {'peer_id': pid}))
        self.service.on('state_changed', lambda state: self._push('state_changed', {'state': state}))
        self.service.on('emergency', lambda sid, sn, msg: self._push('emergency', {'sender_id': sid, 'sender_name': sn, 'message': msg}))

    def _push(self, event, data):
        try:
            js = f"App.onEvent('{event}', '{json.dumps(data).replace(chr(39), chr(92)+chr(39))}')"
            self.webview.evaluate_js(js)
        except Exception as e:
            log.error(f"Push error: {e}")

    def handle(self, payload_json: str) -> str:
        try:
            payload = json.loads(payload_json)
            mid = payload['id']
            method = payload['method']
            args = payload.get('args', [])
            handler = getattr(self, f'_{method}', None)
            if handler:
                result = handler(*args)
                return json.dumps({'id': mid, 'ok': True, 'data': result})
            return json.dumps({'id': mid, 'ok': False, 'error': f'Unknown method: {method}'})
        except Exception as e:
            log.error(f"Handle error: {e}")
            return json.dumps({'id': 0, 'ok': False, 'error': str(e)})

    # --- Callable from JS ---

    def _start_transmitting(self):
        self.service.start_transmitting(self.service._current_channel or '')

    def _stop_transmitting(self):
        self.service.stop_transmitting()

    def _send_text(self, message, channel_id=''):
        self.service.send_text(message, channel_id)

    def _send_emergency(self, message='EMERGENCY'):
        self.service.send_emergency(message)

    def _create_channel(self, name, password=''):
        return self.service.create_channel(name, password)

    def _join_channel(self, channel_id):
        self.service.join_channel(channel_id)

    def _get_channels(self):
        channels = self.service.db.get_all_channels()
        return [{'id': c['id'], 'name': c['name'], 'member_count': c.get('member_count', 0),
                 'is_locked': bool(c.get('is_locked', 0))} for c in channels]

    def _get_devices(self):
        peers = self.service.net.get_connected_peers()
        result = {}
        for pid, p in peers.items():
            result[pid] = {
                'name': p.get('name', 'Unknown'),
                'ip': p.get('ip', ''),
                'online': True,
            }
        db_devices = self.service.db.get_all_devices()
        for d in db_devices:
            if d['id'] not in result:
                result[d['id']] = {
                    'name': d['name'],
                    'ip': d.get('ip_address', ''),
                    'online': False,
                }
        return result

    def _scan_devices(self):
        self.service.net.udp._send_broadcast()

    def _connect_device(self, ip, port=37023):
        return self.service.connect_to_device(ip, port)

    def _get_device_info(self):
        try:
            from plyer import battery
            bat = battery.battery_info.get('percentage', 100)
        except Exception:
            bat = 100
        return {
            'name': self.config.get('device_name') or 'DemonTalk User',
            'id': self.service.net.device_id,
            'battery': bat,
        }

    def _get_settings(self):
        return self.config._data

    def _set_setting(self, section, key, value):
        self.config.set(section, key, value)
