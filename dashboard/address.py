"""Address extraction, geocoding, and Street View / map image fetch."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Iterable

import httpx

from config import Config
from health import lookup_call_address
from models import AddressHit, Transcription

# House number + street with common US suffixes.
HOUSE_STREET_RE = re.compile(
    r"(?i)\b(\d{1,6})\s+"
    r"([A-Z0-9][A-Z0-9\s\.\-]{1,40}?\s+"
    r"(?:RD|ROAD|ST|STREET|AVE|AVENUE|BLVD|BOULEVARD|DR|DRIVE|LN|LANE|"
    r"CT|COURT|CIR|CIRCLE|WAY|HWY|HIGHWAY|PKWY|PARKWAY|PL|PLACE|TR|"
    r"TRAIL|TER|TERRACE|ALY|ALLEY))\b"
)

INTERSECTION_RE = re.compile(
    r"(?i)\b([A-Z][A-Z0-9\s\.\-]{2,30}?\s+"
    r"(?:RD|ROAD|ST|STREET|AVE|AVENUE|BLVD|DR|DRIVE|LN|LANE|CT|HWY|WAY))"
    r"\s+(?:AND|&|AT|@|X)\s+"
    r"([A-Z][A-Z0-9\s\.\-]{2,30}?\s+"
    r"(?:RD|ROAD|ST|STREET|AVE|AVENUE|BLVD|DR|DRIVE|LN|LANE|CT|HWY|WAY))\b"
)

CROSS_OF_RE = re.compile(
    r"(?i)\b(?:CROSS(?:ING)?\s+OF|CORNER\s+OF)\s+"
    r"([A-Z0-9][A-Z0-9\s\.\-]{2,40}?)"
    r"\s+(?:AND|&)\s+"
    r"([A-Z0-9][A-Z0-9\s\.\-]{2,40}?)\b"
)


def extract_addresses(transcript: str) -> list[str]:
    if not transcript:
        return []
    found: list[str] = []
    seen: set[str] = set()

    def add(text: str) -> None:
        cleaned = re.sub(r"\s+", " ", text).strip(" .,;:")
        key = cleaned.upper()
        if len(cleaned) < 6 or key in seen:
            return
        seen.add(key)
        found.append(cleaned)

    for match in HOUSE_STREET_RE.finditer(transcript):
        add(match.group(0))
    for match in INTERSECTION_RE.finditer(transcript):
        add(f"{match.group(1).strip()} & {match.group(2).strip()}")
    for match in CROSS_OF_RE.finditer(transcript):
        add(f"{match.group(1).strip()} & {match.group(2).strip()}")
    return found


def _cache_key(*parts: str) -> str:
    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:20]
    return digest


def geocode_address(
    client: httpx.Client,
    config: Config,
    address: str,
) -> tuple[str, float, float] | None:
    if not config.google_maps_api_key:
        return None
    query = address
    if config.address_default_city and config.address_default_city.lower() not in address.lower():
        query = f"{address}, {config.address_default_city}"
    params: dict[str, str] = {
        "address": query,
        "key": config.google_maps_api_key,
        "region": config.geocode_region,
    }
    if config.geocode_components:
        params["components"] = config.geocode_components
    response = client.get(
        "https://maps.googleapis.com/maps/api/geocode/json",
        params=params,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("status") != "OK" or not data.get("results"):
        return None
    result = data["results"][0]
    loc = result["geometry"]["location"]
    return (
        str(result.get("formatted_address") or address),
        float(loc["lat"]),
        float(loc["lng"]),
    )


def _download_image(client: httpx.Client, url: str, dest: Path) -> Path | None:
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    response = client.get(url)
    if response.status_code != 200:
        return None
    content_type = response.headers.get("content-type", "")
    if "json" in content_type or response.content[:1] == b"{":
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(response.content)
    return dest


def fetch_map_image(
    client: httpx.Client,
    config: Config,
    lat: float,
    lon: float,
) -> Path | None:
    if not config.google_maps_api_key:
        return None
    dest = config.cache_dir / f"map_{_cache_key(str(lat), str(lon))}.jpg"
    url = (
        "https://maps.googleapis.com/maps/api/staticmap"
        f"?center={lat},{lon}&zoom=17&size=640x640&maptype=hybrid"
        f"&markers=color:red%7C{lat},{lon}&key={config.google_maps_api_key}"
    )
    return _download_image(client, url, dest)


def fetch_streetview_image(
    client: httpx.Client,
    config: Config,
    lat: float,
    lon: float,
) -> Path | None:
    if not config.google_maps_api_key:
        return None
    dest = config.cache_dir / f"sv_{_cache_key(str(lat), str(lon))}.jpg"
    meta = client.get(
        "https://maps.googleapis.com/maps/api/streetview/metadata",
        params={
            "location": f"{lat},{lon}",
            "key": config.google_maps_api_key,
        },
    )
    if meta.status_code == 200:
        try:
            if meta.json().get("status") != "OK":
                return None
        except Exception:  # noqa: BLE001
            pass
    url = (
        "https://maps.googleapis.com/maps/api/streetview"
        f"?size=640x640&location={lat},{lon}&fov=80&pitch=0"
        f"&key={config.google_maps_api_key}"
    )
    return _download_image(client, url, dest)


def resolve_address_hit(
    config: Config,
    transcription: Transcription,
    seen_addresses: set[str],
) -> AddressHit | None:
    """Build an AddressHit for the first new address on this transcription."""
    candidates: list[str] = []
    lat: float | None = None
    lon: float | None = None
    preferred: str | None = None

    db_address, db_lat, db_lon = lookup_call_address(config, transcription.call_id)
    if db_address:
        preferred = db_address
        candidates.append(db_address)
    if db_lat is not None and db_lon is not None:
        lat, lon = db_lat, db_lon

    candidates.extend(extract_addresses(transcription.transcript))
    if not candidates and lat is None:
        return None

    with httpx.Client(timeout=20.0, follow_redirects=True) as client:
        formatted = preferred or candidates[0]
        if lat is None or lon is None:
            for candidate in candidates:
                key = candidate.upper()
                if key in seen_addresses:
                    continue
                geocoded = geocode_address(client, config, candidate)
                if not geocoded:
                    continue
                formatted, lat, lon = geocoded
                break
            else:
                return None

        norm = formatted.upper()
        if norm in seen_addresses:
            return None
        seen_addresses.add(norm)

        map_path = fetch_map_image(client, config, lat, lon)
        sv_path = fetch_streetview_image(client, config, lat, lon)
        if not map_path and not sv_path:
            # Still show overlay text if geocode worked but images failed.
            pass

        snippet = transcription.transcript
        if len(snippet) > 220:
            snippet = snippet[:217] + "…"

        return AddressHit(
            call_id=transcription.call_id,
            raw_text=candidates[0] if candidates else formatted,
            formatted_address=formatted,
            lat=lat,
            lon=lon,
            map_path=str(map_path) if map_path else None,
            streetview_path=str(sv_path) if sv_path else None,
            system_label=transcription.system_label,
            talkgroup_label=transcription.talkgroup_label,
            transcript_snippet=snippet,
        )


def find_new_address_hits(
    config: Config,
    transcriptions: Iterable[Transcription],
    seen_call_ids: set[str],
    seen_addresses: set[str],
) -> list[AddressHit]:
    hits: list[AddressHit] = []
    for row in transcriptions:
        if not row.call_id or row.call_id in seen_call_ids:
            continue
        seen_call_ids.add(row.call_id)
        if not row.transcript and not config.postgres_dsn:
            continue
        try:
            hit = resolve_address_hit(config, row, seen_addresses)
        except Exception:  # noqa: BLE001 — keep feed alive on one bad address
            continue
        if hit:
            hits.append(hit)
    return hits
