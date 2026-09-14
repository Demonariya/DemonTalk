"""Audio processing - noise suppression, gain, VAD."""
import struct
import array
from app.utils.logger import setup_logger

log = setup_logger('AudioProc')


def apply_gain(data: bytes, gain: float) -> bytes:
    if gain == 1.0:
        return data
    samples = struct.unpack(f'<{len(data)//2}h', data)
    result = struct.pack(f'<{len(samples)}h', *[
        max(-32768, min(32767, int(s * gain))) for s in samples
    ])
    return result


def compute_amplitude(data: bytes) -> float:
    if len(data) < 2:
        return 0.0
    samples = struct.unpack(f'<{len(data)//2}h', data)
    rms = (sum(s * s for s in samples) / len(samples)) ** 0.5
    return min(rms / 32768.0, 1.0)


def simple_noise_gate(data: bytes, threshold: float = 0.02) -> bytes:
    if len(data) < 2:
        return data
    samples = array.array('h', data)
    amp = compute_amplitude(data)
    if amp < threshold:
        return b'\x00' * len(data)
    return bytes(samples)


def normalize_audio(data: bytes, target_level: float = 0.5) -> bytes:
    if len(data) < 2:
        return data
    samples = struct.unpack(f'<{len(data)//2}h', data)
    peak = max(abs(s) for s in samples) or 1
    gain = (32768 * target_level) / peak
    return struct.pack(f'<{len(samples)}h', *[
        max(-32768, min(32767, int(s * gain))) for s in samples
    ])


def compute_waveform(data: bytes, bars: int = 32) -> list:
    if len(data) < 2:
        return [0.0] * bars
    samples = struct.unpack(f'<{len(data)//2}h', data)
    chunk_size = max(1, len(samples) // bars)
    result = []
    for i in range(bars):
        start = i * chunk_size
        end = min(start + chunk_size, len(samples))
        chunk = samples[start:end]
        if chunk:
            rms = (sum(s * s for s in chunk) / len(chunk)) ** 0.5
            result.append(min(rms / 32768.0, 1.0))
        else:
            result.append(0.0)
    return result
