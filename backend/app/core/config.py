from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "AI Options Trading Platform"
    env: str = "development"
    secret_key: str = "dev-secret-change-me"
    access_token_expire_minutes: int = 10080  # 7 days
    algorithm: str = "HS256"

    database_url: str = "sqlite:///./trading.db"
    redis_url: str = ""

    frontend_origin: str = "http://localhost:3000"

    market_data_provider: str = "yfinance"
    nse_option_chain_base: str = "https://www.nseindia.com"

    # Upstox (optional) — enables REAL option-chain data. Token expires daily
    # at 3:30 AM IST; regenerate with `python -m scripts.upstox_login`.
    upstox_api_key: str = ""
    upstox_api_secret: str = ""
    upstox_redirect_uri: str = "https://127.0.0.1"
    upstox_access_token: str = ""

    @property
    def cors_origins(self) -> list[str]:
        origins = {self.frontend_origin, "http://localhost:3000", "http://127.0.0.1:3000"}
        return [o for o in origins if o]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
