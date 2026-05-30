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
    twilio_test_to_number: str = ""

    # FHIR
    fhir_base_url: str = "http://hapi.fhir.org/baseR4"

    # Backend
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    log_level: str = "INFO"
    # Frontend dev origins allowed by CORS
    cors_allow_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # CPU pinning
    always_on_cpu_cores: str = "0-5"


settings = Settings()
