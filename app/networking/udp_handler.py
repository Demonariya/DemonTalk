"""UDP handler for discovery, voice, and low-latency communication."""
import socket
import struct
import threading
import time
from app.config import DISCOVERY_PORT, VOICE_PORT, DISCOVERY_MULTICAST, DISCOVERY_MAGIC
from app.networking.packet import Packet, PacketType
from app.utils.logger import setup_logger

log = setup_logger('UDP')


class UDPHandler:
    def __init__(self, device_id: str, device_name: str):
        self.device_id = device_id
        self.device_name = device_name
        self._running = False
        self._threads = []
        self._callbacks = {}
        self._sock = None
        self._multicast_sock = None
        self._peers = {}

    def on(self, event: str, callback):
        self._callbacks.setdefault(event, []).append(callback)

    def _emit(self, event: str, *args, **kwargs):
        for cb in self._callbacks.get(event, []):
            try:
                cb(*args, **kwargs)
            except Exception as e:
                log.error(f"Callback error on {event}: {e}")

    def start(self):
        if self._running:
            return
        self._running = True
        t = threading.Thread(target=self._discovery_loop, daemon=True, name='udp-discovery')
        t.start()
        self._threads.append(t)
        t2 = threading.Thread(target=self._voice_listener, daemon=True, name='udp-voice')
        t2.start()
        self._threads.append(t2)
        log.info("UDP handler started")

    def stop(self):
        self._running = False
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
        if self._multicast_sock:
            try:
                self._multicast_sock.close()
            except OSError:
                pass
        log.info("UDP handler stopped")

    def _create_discovery_socket(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except AttributeError:
            pass
        sock.settimeout(1.0)
        sock.bind(('', DISCOVERY_PORT))
        try:
            mreq = struct.pack('4s4s', socket.inet_aton(DISCOVERY_MULTICAST), socket.inet_aton('0.0.0.0'))
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        except OSError as e:
            log.warning(f"Multicast join failed: {e}")
        return sock

    def _discovery_loop(self):
        self._multicast_sock = self._create_discovery_socket()
        while self._running:
            try:
                data, addr = self._multicast_sock.recvfrom(4096)
                if data[:4] == DISCOVERY_MAGIC:
                    pkt_data = data[4:]
                    pkt = Packet.decode(pkt_data)
                    if pkt.source_id != self.device_id:
                        self._handle_discovery(pkt, addr[0])
            except socket.timeout:
                self._send_broadcast()
            except OSError:
                if self._running:
                    time.sleep(1)
                    try:
                        self._multicast_sock = self._create_discovery_socket()
                    except OSError:
                        pass
            except Exception as e:
                log.error(f"Discovery error: {e}")

    def _send_broadcast(self):
        if not self._multicast_sock:
            return
        pkt = Packet.discovery(self.device_id, self.device_name, VOICE_PORT)
        data = DISCOVERY_MAGIC + pkt.encode()
        try:
            self._multicast_sock.sendto(data, (DISCOVERY_MULTICAST, DISCOVERY_PORT))
        except OSError as e:
            log.debug(f"Broadcast send failed: {e}")

    def _handle_discovery(self, pkt: Packet, ip: str):
        self._peers[pkt.source_id] = {
            'name': pkt.source_name,
            'ip': ip,
            'last_seen': time.time(),
        }
        self._emit('device_found', pkt.source_id, pkt.source_name, ip, pkt.payload)
        if pkt.ptype == PacketType.DISCOVERY:
            resp = Packet.discovery_response(self.device_id, self.device_name, VOICE_PORT)
            data = DISCOVERY_MAGIC + resp.encode()
            try:
                self._multicast_sock.sendto(data, (ip, DISCOVERY_PORT))
            except OSError:
                pass

    def _voice_listener(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except AttributeError:
            pass
        sock.settimeout(1.0)
        sock.bind(('', VOICE_PORT))
        self._sock = sock
        while self._running:
            try:
                data, addr = sock.recvfrom(8192)
                if len(data) > 4 and data[:4] == DISCOVERY_MAGIC:
                    pkt = Packet.decode(data[4:])
                    if pkt.source_id != self.device_id:
                        self._handle_voice_packet(pkt, addr[0])
            except socket.timeout:
                continue
            except OSError:
                if self._running:
                    time.sleep(0.5)
            except Exception as e:
                log.error(f"Voice recv error: {e}")

    def _handle_voice_packet(self, pkt: Packet, ip: str):
        if pkt.ptype == PacketType.VOICE_DATA:
            sep = pkt.payload.find(b'\x00')
            if sep >= 0:
                audio_data = pkt.payload[sep + 1:]
                self._emit('voice_data', pkt.source_id, pkt.source_name, audio_data, ip)
        elif pkt.ptype == PacketType.TEXT_MESSAGE:
            try:
                meta = __import__('json').loads(pkt.payload)
                self._emit('text_message', pkt.source_id, pkt.source_name, meta.get('msg', ''), ip)
            except Exception:
                pass
        elif pkt.ptype == PacketType.HEARTBEAT:
            self._peers[pkt.source_id] = {
                'name': pkt.source_name,
                'ip': ip,
                'last_seen': time.time(),
            }
            self._emit('heartbeat', pkt.source_id, pkt.source_name, ip)
        elif pkt.ptype == PacketType.EMERGENCY:
            try:
                meta = __import__('json').loads(pkt.payload)
                self._emit('emergency', pkt.source_id, pkt.source_name, meta.get('msg', ''), ip)
            except Exception:
                pass

    def send_voice(self, audio_data: bytes, channel_id: str = '', target_ip: str = None):
        pkt = Packet.voice(self.device_id, self.device_name, audio_data, channel_id)
        data = DISCOVERY_MAGIC + pkt.encode()
        try:
            if target_ip:
                self._sock.sendto(data, (target_ip, VOICE_PORT))
            else:
                self._sock.sendto(data, (DISCOVERY_MULTICAST, VOICE_PORT))
        except OSError as e:
            log.debug(f"Voice send failed: {e}")

    def send_text(self, message: str, channel_id: str = '', target_ip: str = None):
        import uuid
        pkt = Packet.text(self.device_id, self.device_name, message, channel_id, str(uuid.uuid4()))
        data = DISCOVERY_MAGIC + pkt.encode()
        try:
            if target_ip:
                self._sock.sendto(data, (target_ip, VOICE_PORT))
            else:
                self._sock.sendto(data, (DISCOVERY_MULTICAST, VOICE_PORT))
        except OSError as e:
            log.debug(f"Text send failed: {e}")

    def send_heartbeat(self):
        pkt = Packet.heartbeat(self.device_id, self.device_name)
        data = DISCOVERY_MAGIC + pkt.encode()
        try:
            self._multicast_sock.sendto(data, (DISCOVERY_MULTICAST, DISCOVERY_PORT))
        except OSError:
            pass

    def send_emergency(self, message: str = 'EMERGENCY'):
        pkt = Packet.emergency(self.device_id, self.device_name, message)
        data = DISCOVERY_MAGIC + pkt.encode()
        try:
            self._sock.sendto(data, (DISCOVERY_MULTICAST, VOICE_PORT))
            self._multicast_sock.sendto(data, (DISCOVERY_MULTICAST, DISCOVERY_PORT))
        except OSError:
            pass

    def get_peers(self):
        now = time.time()
        return {
            pid: p for pid, p in self._peers.items()
            if now - p['last_seen'] < 15
        }
