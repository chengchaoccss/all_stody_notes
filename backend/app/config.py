from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "video-to-notes"
    api_prefix: str = "/api"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    storage_root: Path = Path("/data")
    max_upload_mb: int = 1024

    database_url: str = "postgresql+psycopg2://postgres:postgres@db:5432/v2n"
    redis_url: str = "redis://redis:6379/0"

    volc_ak: str = ""
    volc_sk: str = ""
    volc_asr_app_id: str = ""
    volc_asr_access_token: str = ""
    volc_asr_cluster: str = "volcengine_input_common"
    volc_asr_submit_url: str = "https://openspeech.bytedance.com/api/v1/auc/submit"
    volc_asr_query_url: str = "https://openspeech.bytedance.com/api/v1/auc/query"

    ark_api_key: str = ""
    ark_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    ark_model: str = "doubao-pro-32k"

    public_file_base_url: str = "http://localhost:8000/files"

    @property
    def uploads_dir(self) -> Path:
        return self.storage_root / "uploads"

    @property
    def audio_dir(self) -> Path:
        return self.storage_root / "audio"

    @property
    def subtitles_dir(self) -> Path:
        return self.storage_root / "subtitles"

    @property
    def notes_dir(self) -> Path:
        return self.storage_root / "notes"


settings = Settings()
for d in (settings.uploads_dir, settings.audio_dir, settings.subtitles_dir, settings.notes_dir):
    d.mkdir(parents=True, exist_ok=True)
