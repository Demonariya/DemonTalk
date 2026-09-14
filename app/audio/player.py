"""Audio player for voice playback."""
import threading
import queue
import struct
from app.config import AppConfig
from app.utils.logger import setup_logger

log = setup_logger('Player')


class AudioPlayer:
    def __init__(self):
        self.config = AppConfig()
        self._playing = False
        self._queue = queue.Queue(maxsize=50)
        self._thread = None
        self._stream = None
        self._volume = 0.8

    @property
    def is_playing(self):
        return self._playing

    def set_volume(self, vol: float):
        self._volume = max(0.0, min(1.0, vol))

    def start(self):
        if self._playing:
            return
        self._playing = True
        self._thread = threading.Thread(target=self._play_loop, daemon=True, name='audio-player')
        self._thread.start()

    def stop(self):
        self._playing = False
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    def feed(self, audio_data: bytes):
        try:
            self._queue.put_nowait(audio_data)
        except queue.Full:
            try:
                self._queue.get_nowait()
                self._queue.put_nowait(audio_data)
            except queue.Empty:
                pass

    def _play_loop(self):
        try:
            import pyaudiowpatch as pyaudio
        except ImportError:
            try:
                import pyaudio
            except ImportError:
                log.warning("PyAudio not available, dropping audio")
                self._simulate_play()
                return

        pa = pyaudio.PyAudio()
        try:
            self._stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                output=True,
                frames_per_buffer=960,
            )
            while self._playing:
                try:
                    data = self._queue.get(timeout=0.1)
                    if self._volume < 1.0:
                        data = self._adjust_volume(data, self._volume)
                    self._stream.write(data)
                except queue.Empty:
                    continue
        except Exception as e:
            log.error(f"Player error: {e}")
        finally:
            if self._stream:
                try:
                    self._stream.stop_stream()
                    self._stream.close()
                except Exception:
                    pass
            try:
                pa.terminate()
            except Exception:
                pass

    def _simulate_play(self):
        import time
        while self._playing:
            try:
                self._queue.get(timeout=0.1)
            except queue.Empty:
                continue

    def _adjust_volume(self, data: bytes, volume: float) -> bytes:
        samples = struct.unpack(f'<{len(data)//2}h', data)
        adjusted = tuple(max(-32768, min(32767, int(s * volume))) for s in samples)
        return struct.pack(f'<{len(adjusted)}h', *adjusted)

    def play_notification(self, sound_type: str = 'default'):
        tone = {
            'connect': [800, 0.1, 1000, 0.1],
            'disconnect': [1000, 0.1, 800, 0.1],
            'transmit': [600, 0.05],
            'receive': [1200, 0.05],
            'message': [900, 0.08, 1100, 0.08],
            'emergency': [400, 0.2, 600, 0.2, 400, 0.2],
        }.get(sound_type, [800, 0.1])
        t = threading.Thread(target=self._play_tone_sequence, args=(tone,), daemon=True)
        t.start()

    def _play_tone_sequence(self, tones):
        try:
            import pyaudiowpatch as pyaudio
        except ImportError:
            try:
                import pyaudio
            except ImportError:
                return
        pa = pyaudio.PyAudio()
        try:
            stream = pa.open(format=pyaudio.paInt16, channels=1, rate=16000, output=True)
            i = 0
            while i < len(tones) - 1:
                freq = tones[i]
                duration = tones[i + 1]
                n_samples = int(16000 * duration)
                buf = struct.pack(f'<{n_samples}h', *[
                    int(16000 * 0.3 * __import__('math').sin(2 * __import__('math').pi * freq * t / 16000))
                    for t in range(n_samples)
                ])
                stream.write(buf)
                i += 2
            stream.stop_stream()
            stream.close()
        except Exception:
            pass
        finally:
            try:
                pa.terminate()
            except Exception:
                pass
