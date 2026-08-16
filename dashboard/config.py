"""Load dashboard settings from environment / .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

DASHBOARD_DIR = Path(__file__).resolve().parent
CACHE_DIR = DASHBOARD_DIR / "cache"
ENV_PATH = DASHBOARD_DIR / ".env"

DEFAULT_SYSTEMS = (11, 7, 56, 57, 58, 59, 60, 61)

SYSTEM_LABELS = {
    11: "Jay",
    7: "Randolph",
    56: "Blackford",
    57: "Wells",
    58: "Adams",
    59: "Delaware",
    60: "State Interop",
    61: "AirMed",
}


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return float(raw)


def _csv_ints(name: str, default: tuple[int, ...]) -> tuple[int, ...]:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return tuple(int(part.strip()) for part in raw.split(",") if part.strip())


@dataclass(frozen=True)
class Config:
    pulse_api_base: str = "https://data.countypulsenetwork.com/api/transcriptions"
    pulse_system_ids: tuple[int, ...] = DEFAULT_SYSTEMS
    pulse_poll_seconds: int = 300

    postgres_dsn: str = ""
    call_stale_seconds: int = 120
    health_poll_seconds: int = 5

    remote_host: str = ""
    remote_tcp_port: int = 5432
    tlr_health_url: str = ""
    tlr_health_user: str = ""
    tlr_health_password: str = ""

    google_maps_api_key: str = ""
    geocode_region: str = "us"
    geocode_components: str = "administrative_area:IN|country:US"
    address_overlay_seconds: int = 25
    address_default_city: str = ""

    publer_api_key: str = ""
    publer_workspace_id: str = ""
    publer_poll_seconds: int = 120

    window_width: int = 1080
    window_height: int = 1920

    cache_dir: Path = field(default_factory=lambda: CACHE_DIR)

    @property
    def system_labels(self) -> dict[int, str]:
        return dict(SYSTEM_LABELS)


def load_config(env_path: Path | None = None) -> Config:
    path = env_path or ENV_PATH
    load_dotenv(path, override=False)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return Config(
        pulse_api_base=os.getenv(
            "PULSE_API_BASE",
            "https://data.countypulsenetwork.com/api/transcriptions",
        ).rstrip("/"),
        pulse_system_ids=_csv_ints("PULSE_SYSTEM_IDS", DEFAULT_SYSTEMS),
        pulse_poll_seconds=_int("PULSE_POLL_SECONDS", 300),
        postgres_dsn=os.getenv("POSTGRES_DSN", "").strip(),
        call_stale_seconds=_int("CALL_STALE_SECONDS", 120),
        health_poll_seconds=_int("HEALTH_POLL_SECONDS", 5),
        remote_host=os.getenv("REMOTE_HOST", "").strip(),
        remote_tcp_port=_int("REMOTE_TCP_PORT", 5432),
        tlr_health_url=os.getenv("TLR_HEALTH_URL", "").strip(),
        tlr_health_user=os.getenv("TLR_HEALTH_USER", "").strip(),
        tlr_health_password=os.getenv("TLR_HEALTH_PASSWORD", "").strip(),
        google_maps_api_key=os.getenv("GOOGLE_MAPS_API_KEY", "").strip(),
        geocode_region=os.getenv("GEOCODE_REGION", "us").strip() or "us",
        geocode_components=os.getenv(
            "GEOCODE_COMPONENTS",
            "administrative_area:IN|country:US",
        ).strip(),
        address_overlay_seconds=_int("ADDRESS_OVERLAY_SECONDS", 25),
        address_default_city=os.getenv("ADDRESS_DEFAULT_CITY", "").strip(),
        publer_api_key=os.getenv("PUBLER_API_KEY", "").strip(),
        publer_workspace_id=os.getenv("PUBLER_WORKSPACE_ID", "").strip(),
        publer_poll_seconds=_int("PUBLER_POLL_SECONDS", 120),
        window_width=_int("WINDOW_WIDTH", 1080),
        window_height=_int("WINDOW_HEIGHT", 1920),
        cache_dir=CACHE_DIR,
    )
