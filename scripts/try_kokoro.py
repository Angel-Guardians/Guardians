"""Quick Kokoro TTS check — synthesize text to a WAV you can listen to.

Runs the exact backend path the voice WebSocket uses
(`backend.voice.synthesize_pcm` + `voice_for_route`), writes a 24 kHz 16-bit mono
WAV, and (on Windows) can play it back.

Run from the repo root with the project interpreter:

    C:/Python313/python.exe scripts/try_kokoro.py
    C:/Python313/python.exe scripts/try_kokoro.py --route safety --play
    C:/Python313/python.exe scripts/try_kokoro.py --voice af_nicole -t "Your heart rate is 72 bpm." --play
    C:/Python313/python.exe scripts/try_kokoro.py --list        # show routes + voices

Notes:
  * --voice overrides --route. With neither, uses the Kokoro default voice.
  * First run loads the model (~20 s, one-time); later runs are fast.
  * Picks whatever TTS_BACKEND resolves to (kokoro by default; falls back to
    OpenAI only if Kokoro can't load).
"""
from __future__ import annotations

import argparse
import sys
import time
import wave
from pathlib import Path

# Allow running as `python scripts/try_kokoro.py` from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.voice import TTS_SAMPLE_RATE, synthesize_pcm, voice_for_route  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Synthesize text with Kokoro and save/play a WAV.")
    parser.add_argument(
        "-t",
        "--text",
        default="Good morning Eleanor. It's 8:00 AM — time for your 10 mg Lisinopril.",
        help="Text to speak.",
    )
    parser.add_argument(
        "--route",
        choices=["safety", "health", "reminder", "companion", "behavior", "caregiver"],
        help="Pick the specialist voice for this route.",
    )
    parser.add_argument("--voice", help="Explicit voice id (overrides --route), e.g. af_heart.")
    parser.add_argument("-o", "--out", default="kokoro_out.wav", help="Output WAV path.")
    parser.add_argument("--play", action="store_true", help="Play the WAV after writing (Windows).")
    parser.add_argument("--list", action="store_true", help="List routes/voices and exit.")
    args = parser.parse_args()

    if args.list:
        from backend.voice.kokoro_tts import _KOKORO_VOICE_BY_ROUTE

        print("Route -> Kokoro voice:")
        for route, voice in _KOKORO_VOICE_BY_ROUTE.items():
            print(f"  {route:10} {voice}")
        print("\nMore voices to try with --voice: af_heart, af_bella, af_nicole, af_sky, "
              "af_sarah, am_michael, am_adam, am_echo, bf_emma, bm_george")
        return 0

    voice = args.voice or voice_for_route(args.route)

    print(f"text  : {args.text!r}")
    print(f"voice : {voice}  (route={args.route or '-'})")
    print("synthesizing... (first run loads the model, ~20 s)")

    start = time.time()
    pcm = b"".join(synthesize_pcm(args.text, voice))
    elapsed = time.time() - start

    if not pcm:
        print("ERROR: no audio produced (empty text?).", file=sys.stderr)
        return 1

    out = Path(args.out).resolve()
    with wave.open(str(out), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)  # 16-bit
        wav.setframerate(TTS_SAMPLE_RATE)
        wav.writeframes(pcm)

    seconds = len(pcm) / 2 / TTS_SAMPLE_RATE
    print(f"wrote : {out}")
    print(f"audio : {seconds:.2f}s @ {TTS_SAMPLE_RATE} Hz  ({len(pcm):,} bytes, synth {elapsed:.1f}s)")

    if args.play:
        try:
            import winsound

            print("playing...")
            winsound.PlaySound(str(out), winsound.SND_FILENAME)
        except Exception as exc:  # noqa: BLE001
            print(f"(could not auto-play: {exc} — open {out.name} in any player)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
