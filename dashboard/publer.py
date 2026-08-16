"""Publer last-posts client."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from config import Config
from models import PublerPost, parse_timestamp


def _post_text(item: dict[str, Any]) -> str:
    for key in ("text", "title", "caption", "description"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    # Nested network payloads
    networks = item.get("networks") or item.get("accounts") or []
    if isinstance(networks, list):
        for net in networks:
            if not isinstance(net, dict):
                continue
            content = net.get("content") or net.get("text") or net.get("title")
            if isinstance(content, str) and content.strip():
                return content.strip()
            if isinstance(content, dict):
                for key in ("text", "title", "message"):
                    if isinstance(content.get(key), str) and content[key].strip():
                        return content[key].strip()
    return ""


def _networks(item: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for key in ("networks", "network", "platforms"):
        value = item.get(key)
        if isinstance(value, str):
            names.append(value)
        elif isinstance(value, list):
            for entry in value:
                if isinstance(entry, str):
                    names.append(entry)
                elif isinstance(entry, dict):
                    label = (
                        entry.get("name")
                        or entry.get("provider")
                        or entry.get("type")
                        or entry.get("network")
                    )
                    if label:
                        names.append(str(label))
    accounts = item.get("accounts") or []
    if isinstance(accounts, list):
        for account in accounts:
            if isinstance(account, dict):
                provider = account.get("provider") or account.get("type")
                if provider:
                    names.append(str(provider))
    # Dedupe preserve order
    seen: set[str] = set()
    ordered: list[str] = []
    for name in names:
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(name)
    return ordered


def _account_names(item: dict[str, Any]) -> list[str]:
    names: list[str] = []
    accounts = item.get("accounts") or []
    if isinstance(accounts, list):
        for account in accounts:
            if isinstance(account, dict):
                label = (
                    account.get("name")
                    or account.get("username")
                    or account.get("display_name")
                )
                if label:
                    names.append(str(label))
    return names


def _thumbnail(item: dict[str, Any]) -> str | None:
    for key in ("thumbnail", "thumbnail_url", "image", "media_url"):
        value = item.get(key)
        if isinstance(value, str) and value.startswith("http"):
            return value
        if isinstance(value, dict):
            url = value.get("url") or value.get("src")
            if isinstance(url, str) and url.startswith("http"):
                return url
    media = item.get("media") or item.get("images") or []
    if isinstance(media, list) and media:
        first = media[0]
        if isinstance(first, str) and first.startswith("http"):
            return first
        if isinstance(first, dict):
            url = first.get("url") or first.get("src") or first.get("thumbnail")
            if isinstance(url, str) and url.startswith("http"):
                return url
    return None


def _normalize_posts(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("posts", "data", "results", "items"):
            nested = payload.get(key)
            if isinstance(nested, list):
                return [row for row in nested if isinstance(row, dict)]
    return []


def fetch_recent_posts(config: Config, limit: int = 3) -> tuple[list[PublerPost], str | None]:
    if not config.publer_api_key:
        return [], "PUBLER_API_KEY not configured"
    if not config.publer_workspace_id:
        return [], "PUBLER_WORKSPACE_ID not configured"

    headers = {
        "Authorization": f"Bearer-API {config.publer_api_key}",
        "Publer-Workspace-Id": config.publer_workspace_id,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    params = {
        "state": "published",
        "page": 0,
    }
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            response = client.get(
                "https://app.publer.com/api/v1/posts",
                headers=headers,
                params=params,
            )
            if response.status_code >= 400:
                return [], f"Publer HTTP {response.status_code}: {response.text[:160]}"
            rows = _normalize_posts(response.json())
    except Exception as exc:  # noqa: BLE001
        return [], str(exc)

    posts: list[PublerPost] = []
    for row in rows:
        post_id = str(row.get("id") or row.get("_id") or row.get("post_id") or "")
        published = parse_timestamp(
            row.get("published_at")
            or row.get("publish_at")
            or row.get("posted_at")
            or row.get("updated_at")
        )
        scheduled = parse_timestamp(
            row.get("scheduled_at") or row.get("schedule_at") or row.get("created_at")
        )
        posts.append(
            PublerPost(
                post_id=post_id,
                text=_post_text(row),
                networks=_networks(row),
                scheduled_at=scheduled,
                published_at=published,
                state=str(row.get("state") or row.get("status") or "published"),
                thumbnail_url=_thumbnail(row),
                account_names=_account_names(row),
            )
        )

    posts.sort(
        key=lambda p: p.when or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return posts[:limit], None
