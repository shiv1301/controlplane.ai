from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    api_key_secret: str = "change_me_to_a_secure_secret"
    admin_api_key: str = "change_me_too"
    
    database_url: str = "postgresql+asyncpg://controlplane:password@localhost:5432/controlplane"
    redis_url: str = "redis://localhost:6379/0"
    
    ollama_base_url: str = "http://localhost:11434"
    default_model: str = "qwen3:1.7b"
    compression_model: str = "qwen3:1.7b"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
