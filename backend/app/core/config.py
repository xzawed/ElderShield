import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str
    admin_api_key: str
    device_api_key: str


def load_settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL", "sqlite:///./eldershield.db"),
        admin_api_key=os.getenv("ADMIN_API_KEY", "change-me-admin"),
        device_api_key=os.getenv("DEVICE_API_KEY", "change-me-device"),
    )


settings = load_settings()
