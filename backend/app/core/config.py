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
    nextdns_api_key: str | None = None
    nextdns_profile_id: str | None = None
    admin_notify_webhook_url: str | None = None
    enroll_skip_integrity: bool = False
    play_integrity_enabled: bool = False
    play_package_name: str = "com.eldershield"
    enroll_max_per_window: int = 10
    enroll_rate_limit_per_minute: int = 20


def load_settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL", "sqlite:///./eldershield.db"),
        admin_api_key=os.getenv("ADMIN_API_KEY", "change-me-admin"),
        device_api_key=os.getenv("DEVICE_API_KEY", "change-me-device"),
        nextdns_api_key=os.getenv("NEXTDNS_API_KEY") or None,
        nextdns_profile_id=os.getenv("NEXTDNS_PROFILE_ID") or None,
        admin_notify_webhook_url=os.getenv("ADMIN_NOTIFY_WEBHOOK_URL") or None,
        enroll_skip_integrity=os.getenv("ELDERSHIELD_ENROLL_SKIP_INTEGRITY") == "1",
        play_integrity_enabled=os.getenv("PLAY_INTEGRITY_ENABLED") == "1",
        play_package_name=os.getenv("PLAY_PACKAGE_NAME", "com.eldershield"),
        enroll_max_per_window=int(os.getenv("ENROLL_MAX_PER_WINDOW", "10")),
        enroll_rate_limit_per_minute=int(os.getenv("ENROLL_RATE_LIMIT_PER_MINUTE", "20")),
    )


def assert_secure_settings(settings: Settings, *, allow_insecure: bool = False) -> None:
    """Refuse known placeholder keys, identical keys, and production Integrity skip."""
    allow = allow_insecure or os.getenv("ELDERSHIELD_ALLOW_INSECURE_DEFAULTS") == "1"
    if settings.enroll_skip_integrity and not allow:
        raise RuntimeError(
            "ELDERSHIELD_ENROLL_SKIP_INTEGRITY requires "
            "ELDERSHIELD_ALLOW_INSECURE_DEFAULTS=1 (lab only)"
        )
    if allow:
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
