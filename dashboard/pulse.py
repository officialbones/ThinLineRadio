"""County Pulse transcription API client."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from config import Config, SYSTEM_LABELS
from models import ActivitySnapshot, Transcription

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


def _normalize_rows(payload: Any) -> list[dict[str, Any]]:
    if payload is None:
        return []
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("transcriptions", "data", "results", "items", "rows"):
            nested = payload.get(key)
            if isinstance(nested, list):
                return [row for row in nested if isinstance(row, dict)]
        # Single object
        if "callId" in payload or "transcript" in payload:
            return [payload]
    return []


def fetch_system_transcriptions(
    client: httpx.Client,
    base_url: str,
    system_id: int,
    start: datetime,
    end: datetime,
    limit: int = 5000,
) -> list[Transcription]:
    start_utc = start.astimezone(timezone.utc)
    end_utc = end.astimezone(timezone.utc)
    # Try ISO first (common for HTTP APIs), then unix seconds as used by some sweep scripts.
    param_sets = [
        {
            "system_id": system_id,
            "start": start_utc.isoformat().replace("+00:00", "Z"),
            "end": end_utc.isoformat().replace("+00:00", "Z"),
            "limit": limit,
        },
        {
            "system_id": system_id,
            "start": int(start_utc.timestamp()),
            "end": int(end_utc.timestamp()),
            "limit": limit,
        },
    ]
    last_error: Exception | None = None
    for params in param_sets:
        try:
            response = client.get(base_url, params=params, headers=BROWSER_HEADERS)
            response.raise_for_status()
            rows = _normalize_rows(response.json())
            return [Transcription.from_api(row) for row in rows]
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            continue
    assert last_error is not None
    raise last_error


def fetch_activity(config: Config, window_minutes: int = 5) -> ActivitySnapshot:
    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=window_minutes)
    by_call: dict[str, Transcription] = {}
    errors: list[str] = []

    timeout = httpx.Timeout(60.0, connect=15.0)
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        for system_id in config.pulse_system_ids:
            try:
                rows = fetch_system_transcriptions(
                    client,
                    config.pulse_api_base,
                    system_id,
                    start,
                    end,
                )
                for row in rows:
                    # Prefer richer labels when the API omits them.
                    system_label = row.system_label or SYSTEM_LABELS.get(
                        system_id, f"System {system_id}"
                    )
                    if not row.system_label or row.system_id is None:
                        row = Transcription(
                            call_id=row.call_id,
                            system_id=row.system_id or system_id,
                            system_label=system_label,
                            talkgroup_id=row.talkgroup_id,
                            talkgroup_label=row.talkgroup_label,
                            timestamp=row.timestamp,
                            transcript=row.transcript,
                            transcript_confidence=row.transcript_confidence,
                            audio_duration=row.audio_duration,
                            has_tones=row.has_tones,
                            alert_summary=row.alert_summary,
                        )
                    key = row.call_id or f"{system_id}:{row.timestamp}:{row.transcript[:40]}"
                    by_call[key] = row
            except Exception as exc:  # noqa: BLE001 — surface per-system failures
                label = SYSTEM_LABELS.get(system_id, str(system_id))
                errors.append(f"{label} ({system_id}): {exc}")

    transcriptions = sorted(
        by_call.values(),
        key=lambda t: t.timestamp or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    system_counts = Counter(
        t.system_label or SYSTEM_LABELS.get(t.system_id or -1, "?")
        for t in transcriptions
    )
    tg_counts = Counter(
        f"{t.system_label}: {t.talkgroup_label or t.talkgroup_id or '?'}"
        for t in transcriptions
        if t.talkgroup_label or t.talkgroup_id
    )
    return ActivitySnapshot(
        fetched_at=end,
        window_start=start,
        window_end=end,
        transcriptions=transcriptions,
        by_system=dict(system_counts.most_common()),
        by_talkgroup=dict(tg_counts.most_common(12)),
        tone_count=sum(1 for t in transcriptions if t.has_tones or t.alert_summary),
        error="; ".join(errors) if errors else None,
    )
