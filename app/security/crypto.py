"""Local communication encryption - stdlib only (no cryptography package)."""
import os
import hashlib
import hmac
import struct
import secrets
from app.utils.logger import setup_logger

log = setup_logger('Crypto')

KEY_SIZE = 32
NONCE_SIZE = 16


def generate_device_id():
    raw = secrets.token_hex(16)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def generate_session_key():
    return secrets.token_bytes(KEY_SIZE)


def derive_key(shared_secret: bytes, salt: bytes = b'demontalk_v1') -> bytes:
    return hashlib.pbkdf2_hmac('sha256', shared_secret, salt, 100000, dklen=KEY_SIZE)


def _xor_crypt(key: bytes, data: bytes) -> bytes:
    """XOR stream cipher with HKDF-like key expansion."""
    out = bytearray()
    for i in range(len(data)):
        block_idx = i // KEY_SIZE
        ki = hashlib.sha256(key + block_idx.to_bytes(4, 'big')).digest()
        out.append(data[i] ^ ki[i % KEY_SIZE])
    return bytes(out)


def encrypt_message(key: bytes, plaintext: bytes) -> bytes:
    nonce = secrets.token_bytes(NONCE_SIZE)
    # Derive per-message key
    msg_key = hashlib.sha256(key + nonce).digest()
    ciphertext = _xor_crypt(msg_key, plaintext)
    # HMAC for authentication
    tag = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()[:16]
    return nonce + ciphertext + tag


def decrypt_message(key: bytes, data: bytes) -> bytes:
    if len(data) < NONCE_SIZE + 16:
        raise ValueError("Invalid encrypted data")
    nonce = data[:NONCE_SIZE]
    tag = data[-16:]
    ciphertext = data[NONCE_SIZE:-16]
    # Verify HMAC
    expected = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()[:16]
    if not hmac.compare_digest(tag, expected):
        raise ValueError("Authentication failed")
    msg_key = hashlib.sha256(key + nonce).digest()
    return _xor_crypt(msg_key, ciphertext)


def compute_hmac(key: bytes, data: bytes) -> bytes:
    return hmac.new(key, data, hashlib.sha256).digest()


def verify_hmac(key: bytes, data: bytes, expected: bytes) -> bool:
    return hmac.compare_digest(compute_hmac(key, data), expected)


def generate_pairing_code() -> str:
    return f"{secrets.randbelow(100000):06d}"


def hash_pairing_code(code: str) -> bytes:
    return hashlib.sha256(code.encode()).digest()


class SecureChannel:
    def __init__(self, key: bytes = None):
        self.key = key or generate_session_key()
        self.established = False

    def encrypt(self, data: bytes) -> bytes:
        return encrypt_message(self.key, data)

    def decrypt(self, data: bytes) -> bytes:
        return decrypt_message(self.key, data)

    def sign(self, data: bytes) -> bytes:
        return compute_hmac(self.key, data)

    def verify(self, data: bytes, sig: bytes) -> bool:
        return verify_hmac(self.key, data, sig)
