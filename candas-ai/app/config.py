from functools import lru_cache
from typing import Literal
from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'Agentic Campaign Manager'
    api_version: str = '1.0'
    environment: Literal['local', 'test', 'staging', 'production'] = 'local'
    debug: bool = False
    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: ['http://localhost:3000', 'http://localhost:5173', 'http://localhost:8000']
    )

    database_url: str = 'postgresql+asyncpg://campaign:campaign@postgres:5432/campaign_db'
    redis_url: str = 'redis://redis:6379/0'

    auth_provider: Literal['auth0', 'keycloak', 'local'] = 'local'
    auth0_domain: str | None = None
    auth0_audience: str | None = None
    keycloak_issuer: str | None = None
    keycloak_audience: str | None = None
    jwt_algorithm: str = 'RS256'
    jwt_secret: str = 'dev-secret-change-me'
    auth_disabled_for_local_dev: bool = False

    ollama_base_url: str = 'http://ollama:11434'
    ollama_primary_model: str = 'llama3.1:8b'
    ollama_fallback_model: str = 'llama3:8b'
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    runway_api_key: str | None = None
    image_provider: Literal['placeholder', 'openai', 'pollinations'] = 'placeholder'

    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_s3_bucket: str = 'campaign-assets'
    aws_region: str = 'us-east-1'
    s3_endpoint_url: str | None = 'http://minio:9000'
    s3_public_base_url: str | None = 'http://localhost:9000/campaign-assets'

    pinecone_api_key: str | None = None
    pinecone_index: str | None = None

    logfire_token: str | None = None
    otel_exporter_otlp_endpoint: str | None = None

    webhook_signing_secret: str = 'dev-webhook-secret-change-me'
    moderation_provider: Literal['openai', 'internal'] = 'internal'

    # Platform credentials. Adapters support mock mode locally, but production should set real credentials.
    platform_mock_mode: bool = True
    instagram_access_token: str | None = None
    twitter_bearer_token: str | None = None
    twitter_api_key: str | None = None
    twitter_api_secret: str | None = None
    linkedin_access_token: str | None = None
    tiktok_access_token: str | None = None
    facebook_access_token: str | None = None
    facebook_page_id: str | None = None
    facebook_page_access_token: str | None = None
    meta_graph_version: str = 'v22.0'
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    youtube_access_token: str | None = None

    rate_limit_authenticated: str = '100/minute'
    rate_limit_anonymous: str = '10/minute'


@lru_cache
def get_settings() -> Settings:
    return Settings()
