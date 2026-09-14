# DemonTalk

Offline peer-to-peer walkie-talkie app for Android.

## Features

- Push-to-talk voice communication over local Wi-Fi / hotspot
- UDP multicast device discovery (no internet required)
- TCP reliable text messaging
- Channel system with optional passwords
- AES-256-GCM encryption for local communication
- Dark cyberpunk UI with neon accents
- Audio visualization waveform
- Voice activity detection & noise suppression

## Build

```bash
pip install buildozer
buildozer android debug
```

## Requirements

- Python 3.11+
- Kivy 2.3+
- KivyMD 2.0+
- Buildozer (for Android builds)

## License

MIT
