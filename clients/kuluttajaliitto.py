from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from html import unescape

import httpx

WP_API = "https://www.kuluttajaliitto.fi/wp-json/wp/v2/posts"
LAUSUNTO_TAG_ID = 3606  # tag "lausunto", 199 posts as of 2026-04-22


@dataclass
class Statement:
    id: int
    date: str  # YYYY-MM-DD
    title: str
    excerpt: str
    url: str


def _strip(s: str | None) -> str:
    if not s:
        return ""
    return unescape(re.sub(r"<[^>]+>", " ", s)).strip()


def fetch_statements(client: httpx.Client, per_page: int = 15) -> list[Statement]:
    """Fetch the most recent lausunto posts from the WordPress REST API."""
    r = client.get(
        WP_API,
        params={
            "tags": LAUSUNTO_TAG_ID,
            "per_page": per_page,
            "orderby": "date",
            "order": "desc",
            "_fields": "id,date,title,link,excerpt",
        },
        timeout=20,
    )
    r.raise_for_status()
    return [
        Statement(
            id=p["id"],
            date=p["date"][:10],
            title=_strip(p["title"]["rendered"]),
            excerpt=_strip(p.get("excerpt", {}).get("rendered", "")),
            url=p["link"],
        )
        for p in r.json()
    ]


def build_context(statements: list[Statement]) -> dict:
    return {
        "last_updated": date.today().isoformat(),
        "recent_statements": [
            {
                "title": s.title,
                "date": s.date,
                "url": s.url,
                "excerpt": s.excerpt,
            }
            for s in statements
        ],
    }
