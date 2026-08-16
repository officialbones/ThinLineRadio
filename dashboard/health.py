"""Postgres scanner health and remote host probes."""

from __future__ import annotations

import socket
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
import psycopg

from config import Config
from models import ProbeResult, ProbeStatus, RemoteHealth, ScannerHealth, parse_timestamp

LAST_CALL_SQL = """
SELECT
    c."timestamp" AS call_ts,
    COALESCE(t."label", '') AS talkgroup_label,
    COALESCE(t."name", '') AS talkgroup_name,
    COALESCE(s."label", '') AS system_label,
    s."systemRef" AS system_ref
FROM "calls" c
JOIN "talkgroups" t ON t."talkgroupId" = c."talkgroupId"
JOIN "systems" s ON s."systemId" = c."systemId"
ORDER BY c."timestamp" DESC
LIMIT 1
"""


def check_scanner_health(config: Config) -> ScannerHealth:
    now = datetime.now(timezone.utc)
    if not config.postgres_dsn:
        return ScannerHealth(
            db_ok=False,
            last_call_at=None,
            age_seconds=None,
            stale=True,
            system_label="",
            talkgroup_label="",
            talkgroup_name="",
            system_ref=None,
            error="POSTGRES_DSN not configured",
            checked_at=now,
        )
    try:
        with psycopg.connect(config.postgres_dsn, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute(LAST_CALL_SQL)
                row = cur.fetchone()
        if not row:
            return ScannerHealth(
                db_ok=True,
                last_call_at=None,
                age_seconds=None,
                stale=True,
                system_label="",
                talkgroup_label="",
                talkgroup_name="",
                system_ref=None,
                error="No calls in database",
                checked_at=now,
            )
        call_ts, tg_label, tg_name, sys_label, system_ref = row
        last_call = parse_timestamp(call_ts)
        age = (now - last_call).total_seconds() if last_call else None
        stale = age is None or age > config.call_stale_seconds
        return ScannerHealth(
            db_ok=True,
            last_call_at=last_call,
            age_seconds=age,
            stale=stale,
            system_label=str(sys_label or ""),
            talkgroup_label=str(tg_label or ""),
            talkgroup_name=str(tg_name or ""),
            system_ref=int(system_ref) if system_ref is not None else None,
            error=None,
            checked_at=now,
        )
    except Exception as exc:  # noqa: BLE001
        return ScannerHealth(
            db_ok=False,
            last_call_at=None,
            age_seconds=None,
            stale=True,
            system_label="",
            talkgroup_label="",
            talkgroup_name="",
            system_ref=None,
            error=str(exc),
            checked_at=now,
        )


def _tcp_probe(host: str, port: int, timeout: float = 2.0) -> ProbeResult:
    now = datetime.now(timezone.utc)
    if not host:
        return ProbeResult("Host", ProbeStatus.UNKNOWN, "REMOTE_HOST not set", now)
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return ProbeResult(
                "Host",
                ProbeStatus.OK,
                f"TCP {host}:{port} open",
                now,
            )
    except OSError as exc:
        return ProbeResult("Host", ProbeStatus.DOWN, str(exc), now)


def _postgres_probe(dsn: str) -> ProbeResult:
    now = datetime.now(timezone.utc)
    if not dsn:
        return ProbeResult("Postgres", ProbeStatus.UNKNOWN, "POSTGRES_DSN not set", now)
    try:
        with psycopg.connect(dsn, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        return ProbeResult("Postgres", ProbeStatus.OK, "SELECT 1 ok", now)
    except Exception as exc:  # noqa: BLE001
        return ProbeResult("Postgres", ProbeStatus.DOWN, str(exc), now)


def _tlr_health_probe(config: Config) -> ProbeResult:
    now = datetime.now(timezone.utc)
    url = config.tlr_health_url
    if not url:
        return ProbeResult("ThinLine", ProbeStatus.UNKNOWN, "TLR_HEALTH_URL not set", now)
    auth = None
    if config.tlr_health_user:
        auth = (config.tlr_health_user, config.tlr_health_password)
    try:
        with httpx.Client(timeout=5.0, follow_redirects=True) as client:
            response = client.get(url, auth=auth)
        if response.status_code == 200:
            detail = "live ok"
            try:
                body = response.json()
                if isinstance(body, dict) and body.get("status"):
                    detail = f"status={body.get('status')}"
            except Exception:  # noqa: BLE001
                detail = response.text[:80] or detail
            return ProbeResult("ThinLine", ProbeStatus.OK, detail, now)
        if response.status_code in (401, 403):
            return ProbeResult(
                "ThinLine",
                ProbeStatus.DEGRADED,
                f"HTTP {response.status_code} auth",
                now,
            )
        return ProbeResult(
            "ThinLine",
            ProbeStatus.DOWN,
            f"HTTP {response.status_code}",
            now,
        )
    except Exception as exc:  # noqa: BLE001
        return ProbeResult("ThinLine", ProbeStatus.DOWN, str(exc), now)


def check_remote_health(config: Config) -> RemoteHealth:
    port = config.remote_tcp_port
    if config.remote_host and not port and config.tlr_health_url:
        parsed = urlparse(config.tlr_health_url)
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    host = _tcp_probe(config.remote_host, port or 5432)
    tlr = _tlr_health_probe(config)
    pg = _postgres_probe(config.postgres_dsn)
    return RemoteHealth(
        host_probe=host,
        tlr_probe=tlr,
        postgres_probe=pg,
        checked_at=datetime.now(timezone.utc),
    )


def lookup_call_address(config: Config, call_id: str) -> tuple[str | None, float | None, float | None]:
    """Prefer ThinLine-extracted address / geocode when available."""
    if not config.postgres_dsn or not call_id:
        return None, None, None
    # callId may be numeric in DB
    try:
        call_key: int | str
        call_key = int(call_id)
    except ValueError:
        call_key = call_id
    sql = """
        SELECT
            COALESCE(NULLIF("extractedAddress", ''), NULLIF("incidentAddress", '')),
            "incidentLat",
            "incidentLon"
        FROM "calls"
        WHERE "callId" = %s
        LIMIT 1
    """
    try:
        with psycopg.connect(config.postgres_dsn, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (call_key,))
                row = cur.fetchone()
        if not row:
            return None, None, None
        address, lat, lon = row
        return (
            str(address).strip() if address else None,
            float(lat) if lat is not None else None,
            float(lon) if lon is not None else None,
        )
    except Exception:  # noqa: BLE001
        return None, None, None
