"""Settings loaded from .env via pydantic-settings.

Single source of truth for env-derived config. Everything else imports
`settings` from here.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Always-on
    wakeword_model_path: str = "./models/hey_guardian.onnx"
    wakeword_threshold: float = 0.6
    whisper_model: str = "small.en"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"

    # Text-to-speech for the voice WebSocket. `tts_backend` selects the engine:
    #   "kokoro" — local, offline neural TTS (default; needs the [audio] extra)
    #   "openai" — cloud gpt-4o-mini-tts (needs OPENAI_API_KEY below)
    #   "auto"   — Kokoro if the package is importable, else OpenAI
    # Both render 24 kHz 16-bit mono PCM. Voice is chosen per-specialist at runtime.
    tts_backend: str = "kokoro"
    tts_model: str = "gpt-4o-mini-tts"  # OpenAI backend
    tts_voice: str = "alloy"            # OpenAI default voice / fallback

    # Kokoro backend
    kokoro_voice_default: str = "af_heart"
    kokoro_lang_code: str = "a"  # 'a' = American English
    kokoro_speed: float = 1.0

    # LLM (LEGACY — NOT used by the live conversational path).
    # The running app configures its model in backend/llm/config.py via LLM_* env
    # vars (one model behind the provider-neutral seam). These per-role fields are
    # leftovers from the original tiered design and are kept only so old configs
    # don't error. To change the model, edit .env (LLM_MODEL); see MODELS.md.
    ollama_base_url: str = "http://localhost:11434"
    llm_model_generalist: str = "llama3.1:8b-instruct-q4_K_M"
    llm_model_clinical: str = "meditron:7b"
    llm_model_classifier: str = "phi3.5:mini"

    # Storage — SQLite for zero-setup local dev; override DATABASE_URL with
    # postgresql+psycopg://guardian:guardian@localhost:5432/guardian for pgvector.
    database_url: str = "sqlite:///./guardian.db"
    influxdb_url: str = "http://localhost:8086"
    influxdb_token: str = ""
    influxdb_org: str = "guardian"
    influxdb_bucket: str = "vitals"

    # Wearable
    polar_h10_mac: str = ""

    # Twilio
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""

    # Public URL this server is reachable at (used by Twilio to fetch TTS audio).
    # In local dev: run `ngrok http 8000` and paste the https URL here.
    backend_public_url: str = "http://localhost:8000"

    # OpenAI API key used specifically for TTS (always needs the real OpenAI endpoint).
    openai_api_key: str = ""

    # FHIR
    fhir_base_url: str = "http://hapi.fhir.org/baseR4"

    # Lab records / external health-record sources
    # Where uploaded/fetched result documents (PDFs) are stored on disk.
    lab_documents_dir: str = "./data/lab_documents"
    # LifeLabs MyCareCompass (Ontario portal). No public patient API exists, so
    # PDF upload is the primary path and the crawler is an opt-in convenience.
    lifelabs_base_url: str = "https://on.mycarecompass.lifelabs.com"
    lifelabs_username: str = ""
    lifelabs_password: str = ""
    # Persisted browser session (cookies) so MFA only has to be done once.
    lifelabs_session_dir: str = "./data/lifelabs_session"

    # Backend
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    log_level: str = "INFO"
    # Frontend origins allowed by CORS. The browser sends the *page* origin
    # (the frontend on :3000) when it calls the backend cross-origin (:8080).
    cors_allow_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://10.10.52.255:3000",
        # Tailscale: this node's stable tailnet IP + MagicDNS name (frontend on :3000).
        "http://100.103.166.16:3000",
        "http://gx10-3d68.tailb0d74f.ts.net:3000",
    ]
    # Also admit any private-LAN or Tailscale host on :3000 so other machines reach
    # the backend without re-listing their IPs. allow_credentials forbids a "*"
    # origin, so we match the RFC1918 + Tailscale CGNAT ranges (and MagicDNS) here.
    cors_allow_origin_regex: str = (
        r"http://(localhost|127\.0\.0\.1"
        r"|10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
        r"|192\.168\.\d{1,3}\.\d{1,3}"
        r"|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"
        r"|100\.\d{1,3}\.\d{1,3}\.\d{1,3}"  # Tailscale CGNAT (100.64.0.0/10)
        r"|[a-z0-9-]+\.[a-z0-9-]+\.ts\.net"  # Tailscale MagicDNS
        r"):3000"
    )

    # CPU pinning
    always_on_cpu_cores: str = "0-5"


settings = Settings()
