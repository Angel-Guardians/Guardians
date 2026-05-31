"""On-demand bidirectional voice tier.

The watch streams microphone PCM up a WebSocket; the backend transcribes it
(STT), runs one Guardian turn, synthesises the spoken reply (TTS), and streams
that PCM back down the same socket. See `backend/api/voice.py` for the endpoint
and the wire protocol.

Audio is raw 16-bit little-endian mono PCM in both directions — no container, no
codec negotiation. Uplink is 16 kHz (Whisper-native); downlink is 24 kHz (OpenAI
TTS-native). Opus framing is the obvious next optimisation for cellular links, but
on LAN/Wi-Fi raw PCM (~256 kbps up) is simpler and plenty.
"""
from __future__ import annotations

from backend.voice.stt import transcribe_pcm
from backend.voice.tts import TTS_SAMPLE_RATE, synthesize_pcm, voice_for_route

__all__ = ["transcribe_pcm", "synthesize_pcm", "TTS_SAMPLE_RATE", "voice_for_route"]
