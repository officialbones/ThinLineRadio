"""Shared dataclasses for dashboard workers and UI."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def parse_timestamp(value: Any) -> datetime | None:
    """Normalize API/DB timestamps to aware UTC datetimes."""
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, (int, float)):
        # ThinLine stores unix ms; County Pulse may use seconds or ms.
        ts = float(value)
        if ts > 1e12:
            ts /= 1000.0
        elif ts > 1e10:
            ts /= 1000.0
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.isdigit():
            return parse_timestamp(int(text))
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(
                timezone.utc
            )
        except ValueError:
            return None
    return None


@dataclass(frozen=True)
class Transcription:
    call_id: str
    system_id: int | None
    system_label: str
    talkgroup_id: int | None
    talkgroup_label: str
    timestamp: datetime | None
    transcript: str
    transcript_confidence: float | None
    audio_duration: float | None
    has_tones: bool
    alert_summary: str

    @classmethod
    def from_api(cls, row: dict[str, Any]) -> Transcription:
        call_id = row.get("callId") or row.get("call_id") or row.get("id") or ""
        system_id = row.get("systemId") if "systemId" in row else row.get("system_id")
        talkgroup_id = (
            row.get("talkgroupId") if "talkgroupId" in row else row.get("talkgroup_id")
        )
        conf = row.get("transcriptConfidence")
        if conf is None:
            conf = row.get("transcript_confidence")
        duration = row.get("audioDuration")
        if duration is None:
            duration = row.get("audio_duration")
        has_tones = bool(row.get("hasTones") or row.get("has_tones") or False)
        return cls(
            call_id=str(call_id),
            system_id=int(system_id) if system_id is not None else None,
            system_label=str(
                row.get("systemLabel") or row.get("system_label") or ""
            ).strip(),
            talkgroup_id=int(talkgroup_id) if talkgroup_id is not None else None,
            talkgroup_label=str(
                row.get("talkgroupLabel") or row.get("talkgroup_label") or ""
            ).strip(),
            timestamp=parse_timestamp(row.get("timestamp")),
            transcript=str(row.get("transcript") or "").strip(),
            transcript_confidence=float(conf) if conf is not None else None,
            audio_duration=float(duration) if duration is not None else None,
            has_tones=has_tones,
            alert_summary=str(
                row.get("alertSummary") or row.get("alert_summary") or ""
            ).strip(),
        )


@dataclass
class ActivitySnapshot:
    fetched_at: datetime
    window_start: datetime
    window_end: datetime
    transcriptions: list[Transcription] = field(default_factory=list)
    by_system: dict[str, int] = field(default_factory=dict)
    by_talkgroup: dict[str, int] = field(default_factory=dict)
    tone_count: int = 0
    error: str | None = None


class ProbeStatus(str, Enum):
    OK = "OK"
    DEGRADED = "DEGRADED"
    DOWN = "DOWN"
    UNKNOWN = "UNKNOWN"


@dataclass
class ProbeResult:
    name: str
    status: ProbeStatus
    detail: str = ""
    checked_at: datetime | None = None


@dataclass
class ScannerHealth:
    db_ok: bool
    last_call_at: datetime | None
    age_seconds: float | None
    stale: bool
    system_label: str
    talkgroup_label: str
    talkgroup_name: str
    system_ref: int | None
    error: str | None = None
    checked_at: datetime | None = None

    @property
    def status(self) -> ProbeStatus:
        if not self.db_ok:
            return ProbeStatus.DOWN
        if self.stale or self.last_call_at is None:
            return ProbeStatus.DEGRADED
        return ProbeStatus.OK


@dataclass
class RemoteHealth:
    host_probe: ProbeResult
    tlr_probe: ProbeResult
    postgres_probe: ProbeResult
    checked_at: datetime | None = None

    @property
    def overall(self) -> ProbeStatus:
        statuses = {
            self.host_probe.status,
            self.tlr_probe.status,
            self.postgres_probe.status,
        }
        if ProbeStatus.DOWN in statuses:
            return ProbeStatus.DOWN
        if ProbeStatus.DEGRADED in statuses or ProbeStatus.UNKNOWN in statuses:
            return ProbeStatus.DEGRADED
        return ProbeStatus.OK


@dataclass(frozen=True)
class AddressHit:
    call_id: str
    raw_text: str
    formatted_address: str
    lat: float
    lon: float
    map_path: str | None
    streetview_path: str | None
    system_label: str
    talkgroup_label: str
    transcript_snippet: str


@dataclass(frozen=True)
class PublerPost:
    post_id: str
    text: str
    networks: list[str]
    scheduled_at: datetime | None
    published_at: datetime | None
    state: str
    thumbnail_url: str | None
    account_names: list[str]

    @property
    def when(self) -> datetime | None:
        return self.published_at or self.scheduled_at
