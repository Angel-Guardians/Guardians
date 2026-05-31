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
    # Frontend dev origins allowed by CORS
    cors_allow_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # CPU pinning
    always_on_cpu_cores: str = "0-5"


settings = Settings()
