"""Microphone recorder for voice capture."""
import threading
import time
import struct
import io
from app.config import AppConfig, AUDIO_SAMPLE_RATE, AUDIO_CHANNELS, AUDIO_CHUNK_SIZE
from app.utils.logger import setup_logger

log = setup_logger('Recorder')


class AudioRecorder:
    def __init__(self):
        self.config = AppConfig()
        self._recording = False
        self._stream = None
        self._callbacks = {}
        self._lock = threading.Lock()
        self._frames = []
        self._total_frames = 0

    def on(self, event: str, callback):
        self._callbacks.setdefault(event, []).append(callback)

    def _emit(self, event: str, *args, **kwargs):
        for cb in self._callbacks.get(event, []):
            try:
                cb(*args, **kwargs)
            except Exception as e:
                log.error(f"Callback error: {e}")

    @property
    def is_recording(self):
        return self._recording

    def start(self):
        if self._recording:
            return
        self._recording = True
        self._frames = []
        self._total_frames = 0
        t = threading.Thread(target=self._record_loop, daemon=True, name='mic-record')
        t.start()
        log.info("Recording started")

    def stop(self) -> list:
        self._recording = False
        frames = list(self._frames)
        self._frames = []
        log.info(f"Recording stopped | {self._total_frames} frames")
        return frames

    def _record_loop(self):
        quality = self.config.get('audio', 'quality') or 'balanced'
        from app.config import QUALITY_PRESETS
        preset = QUALITY_PRESETS.get(quality, QUALITY_PRESETS['balanced'])
        sample_rate = preset['sample_rate']
        chunk = preset['chunk']

        try:
            import android.permissions
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.RECORD_AUDIO,
            ])
        except ImportError:
            pass

        try:
            import pyaudiowpatch as pyaudio
        except ImportError:
            try:
                import pyaudio
            except ImportError:
                log.warning("PyAudio not available, using simulation")
                self._simulate_recording(sample_rate, chunk)
                return

        pa = pyaudio.PyAudio()
        try:
            self._stream = pa.open(
                format=pyaudio.paInt16,
                channels=AUDIO_CHANNELS,
                rate=sample_rate,
                input=True,
                frames_per_buffer=chunk // 2,
            )
            while self._recording:
                try:
                    data = self._stream.read(chunk // 2, exception_on_overflow=False)
                    with self._lock:
                        self._frames.append(data)
                        self._total_frames += 1
                    self._emit('audio_chunk', data)
                except Exception as e:
                    log.error(f"Record read error: {e}")
                    break
        except Exception as e:
            log.error(f"Audio setup error: {e}")
            self._simulate_recording(sample_rate, chunk)
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

    def _simulate_recording(self, sample_rate, chunk):
        silence = b'\x00' * chunk
        while self._recording:
            time.sleep(chunk / sample_rate / 2)
            with self._lock:
                self._frames.append(silence)
                self._total_frames += 1
            self._emit('audio_chunk', silence)

    def get_amplitude(self) -> float:
        with self._lock:
            if not self._frames:
                return 0.0
            last = self._frames[-1]
        if len(last) < 2:
            return 0.0
        samples = struct.unpack(f'<{len(last)//2}h', last)
        if not samples:
            return 0.0
        rms = (sum(s * s for s in samples) / len(samples)) ** 0.5
        return min(rms / 32768.0, 1.0)
