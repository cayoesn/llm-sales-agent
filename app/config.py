from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Sales Agent API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = True

    # LLM
    LLM_PROVIDER: str = "ollama"
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "llama7b"
    OLLAMA_TEMPERATURE: float | None = None
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_TEMPERATURE: float | None = None

    GROQ_API_KEY: str | None = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_TEMPERATURE: float | None = None

    # Langfuse
    LANGFUSE_PUBLIC_KEY: str = "pk-lf-demo"
    LANGFUSE_SECRET_KEY: str = "sk-lf-demo"
    LANGFUSE_HOST: str = "http://langfuse:3000"

    # Redis
    REDIS_URL: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
