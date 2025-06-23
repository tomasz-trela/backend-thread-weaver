from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    DATABASE_URL: str = ""

    GOOGLE_AI_STUDIO_API_KEY: str = ""
    SPEAKER_DIARIZATION_TOKEN: str = ""


settings = Settings()
