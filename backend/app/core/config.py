import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

INSECURE_DEFAULT_KEYS = frozenset({"change-me-admin", "change-me-device"})


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


def assert_secure_settings(settings: Settings, *, allow_insecure: bool = False) -> None:
    """Refuse known placeholder keys and identical admin/device keys (startup gate)."""
    if allow_insecure or os.getenv("ELDERSHIELD_ALLOW_INSECURE_DEFAULTS") == "1":
        return
    if (
        settings.admin_api_key in INSECURE_DEFAULT_KEYS
        or settings.device_api_key in INSECURE_DEFAULT_KEYS
    ):
        raise RuntimeError(
            "insecure default API keys are not allowed; set ADMIN_API_KEY and "
            "DEVICE_API_KEY (or ELDERSHIELD_ALLOW_INSECURE_DEFAULTS=1 for local only)"
        )
    if settings.admin_api_key == settings.device_api_key:
        raise RuntimeError("admin and device API keys must differ")


settings = load_settings()
