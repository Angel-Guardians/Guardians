# Guardian backend (FastAPI + LangGraph). Build context is the REPO ROOT so the
# image can bundle the sibling dirs the app and its tests need:
#   docker build -f backend/Dockerfile -t guardian-backend .
FROM python:3.11-slim AS base

# uv for fast, reproducible installs (resolves against the committed uv.lock).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Build tools for psycopg / native wheels, plus the system libraries the local
# voice models need at runtime:
#   espeak-ng   -> phonemizer/misaki fallback for out-of-dictionary tokens
#                  (numbers, times, units) when Kokoro synthesises speech
#   libsndfile1 -> soundfile, used by the Kokoro audio path
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential curl \
        espeak-ng libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- Dependency layer (cached unless project metadata changes) -------------
# pyproject reads README.md + LICENSE, so they must be present to install.
COPY pyproject.toml uv.lock README.md LICENSE ./
# Editable install needs the package dir to exist at install time.
COPY backend ./backend
RUN uv pip install --system -e ".[dev]"

# --- Local voice models (in-process TTS/STT — no cloud, no API key) ---------
# Kokoro-82M (neural TTS) and faster-whisper (STT) run INSIDE the API process on
# the Grace CPU; see backend/voice/{tts,stt}.py. We install a curated subset of
# the [audio] extra rather than the whole group on purpose:
#   * skip openwakeword/sounddevice — the bidirectional voice socket doesn't use
#     the wake-word/mic-capture tier, and tflite-runtime / PortAudio lack reliable
#     aarch64 (DGX Spark) wheels, which would break the build.
#   * pin numpy>=2.1 so Kokoro's resolver can't drag it back to 1.26 (core needs 2.x).
# torch resolves to the CPU aarch64 wheel from PyPI, so no CUDA/sm_121 dependency.
# en_core_web_sm is misaki's optional English tagger model (best-effort; the espeak
# fallback covers G2P if it's absent).
RUN uv pip install --system \
        "numpy>=2.1" \
        "faster-whisper>=1.1" \
        "kokoro>=0.9" \
        "misaki[en]" \
        "soundfile>=0.12" \
        "espeakng-loader" \
    && (python -m spacy download en_core_web_sm \
        || echo "[build] en_core_web_sm unavailable; relying on espeak G2P fallback")

# --- Application + the dirs the task calls out -----------------------------
# backend already copied above; add the rest of the runtime + test surface.
COPY scripts ./scripts
COPY scenarios ./scenarios
COPY tests ./tests

# Grounded-data + DB live here at runtime; ensure the dir exists.
RUN mkdir -p /app/data

EXPOSE 8000

# Healthcheck mirrors the app's /health endpoint.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

# Default: serve the API. Override `command` to run scripts/tests/scenarios, e.g.
#   docker compose run --rm backend pytest
#   docker compose run --rm backend python scripts/seed_patient.py
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
