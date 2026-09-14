"""Network packet protocol for DemonTalk."""
import struct
import json
import time
from enum import IntEnum

PROTOCOL_VERSION = 1
HEADER_FORMAT = '!BBHI'  # version, type, flags, timestamp
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)


class PacketType(IntEnum):
    DISCOVERY = 0x01
    DISCOVERY_RESPONSE = 0x02
    VOICE_DATA = 0x10
    VOICE_START = 0x11
    VOICE_STOP = 0x12
    TEXT_MESSAGE = 0x20
    TEXT_ACK = 0x21
    CHANNEL_JOIN = 0x30
    CHANNEL_LEAVE = 0x31
    CHANNEL_LIST = 0x32
    CHANNEL_INFO = 0x33
    HEARTBEAT = 0x40
    HEARTBEAT_ACK = 0x41
    PAIR_REQUEST = 0x50
    PAIR_RESPONSE = 0x51
    PAIR_CONFIRM = 0x52
    EMERGENCY = 0x60
    ERROR = 0xFF


class PacketFlags:
    ENCRYPTED = 0x01
    COMPRESSED = 0x02
    PRIORITY = 0x04
    ACK_REQUIRED = 0x08
    FRAGMENTED = 0x10
    LAST_FRAGMENT = 0x20


class Packet:
    __slots__ = ('ptype', 'flags', 'timestamp', 'payload', 'source_id', 'source_name')

    def __init__(self, ptype: int, payload: bytes = b'', flags: int = 0,
                 source_id: str = '', source_name: str = ''):
        self.ptype = ptype
        self.flags = flags
        self.timestamp = int(time.time())
        self.payload = payload
        self.source_id = source_id
        self.source_name = source_name

    def encode(self) -> bytes:
        meta = json.dumps({
            'sid': self.source_id,
            'sn': self.source_name,
        }).encode()
        header = struct.pack(HEADER_FORMAT, PROTOCOL_VERSION, self.ptype, self.flags, self.timestamp)
        meta_len = struct.pack('!H', len(meta))
        return header + meta_len + meta + self.payload

    @classmethod
    def decode(cls, data: bytes) -> 'Packet':
        if len(data) < HEADER_SIZE + 2:
            raise ValueError("Packet too small")
        version, ptype, flags, ts = struct.unpack(HEADER_FORMAT, data[:HEADER_SIZE])
        if version != PROTOCOL_VERSION:
            raise ValueError(f"Unsupported protocol version: {version}")
        meta_len = struct.unpack('!H', data[HEADER_SIZE:HEADER_SIZE + 2])[0]
        meta_start = HEADER_SIZE + 2
        meta = json.loads(data[meta_start:meta_start + meta_len])
        payload = data[meta_start + meta_len:]
        pkt = cls(ptype, payload, flags, meta.get('sid', ''), meta.get('sn', ''))
        pkt.timestamp = ts
        return pkt

    @classmethod
    def discovery(cls, device_id: str, device_name: str, port: int, channels: list = None) -> 'Packet':
        payload = json.dumps({
            'port': port,
            'channels': channels or [],
            'version': '1.0.0',
        }).encode()
        return cls(PacketType.DISCOVERY, payload, source_id=device_id, source_name=device_name)

    @classmethod
    def discovery_response(cls, device_id: str, device_name: str, port: int, channels: list = None) -> 'Packet':
        payload = json.dumps({
            'port': port,
            'channels': channels or [],
            'version': '1.0.0',
        }).encode()
        return cls(PacketType.DISCOVERY_RESPONSE, payload, source_id=device_id, source_name=device_name)

    @classmethod
    def voice(cls, device_id: str, device_name: str, audio_data: bytes, channel_id: str = '') -> 'Packet':
        payload = json.dumps({'ch': channel_id}).encode() + b'\x00' + audio_data
        return cls(PacketType.VOICE_DATA, payload, source_id=device_id, source_name=device_name)

    @classmethod
    def text(cls, device_id: str, device_name: str, message: str, channel_id: str = '',
             msg_id: str = '') -> 'Packet':
        payload = json.dumps({
            'msg': message,
            'ch': channel_id,
            'mid': msg_id,
        }).encode()
        return cls(PacketType.TEXT_MESSAGE, payload, flags=PacketFlags.ACK_REQUIRED,
                  source_id=device_id, source_name=device_name)

    @classmethod
    def heartbeat(cls, device_id: str, device_name: str) -> 'Packet':
        return cls(PacketType.HEARTBEAT, source_id=device_id, source_name=device_name)

    @classmethod
    def emergency(cls, device_id: str, device_name: str, message: str = 'EMERGENCY') -> 'Packet':
        payload = json.dumps({'msg': message}).encode()
        return cls(PacketType.EMERGENCY, payload, flags=PacketFlags.PRIORITY,
                  source_id=device_id, source_name=device_name)
