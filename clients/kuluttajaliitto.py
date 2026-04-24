from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from html import unescape

import httpx

WP_API = "https://www.kuluttajaliitto.fi/wp-json/wp/v2/posts"
WP_TAGS_API = "https://www.kuluttajaliitto.fi/wp-json/wp/v2/tags"


@dataclass
class Statement:
    id: int
    date: str  # YYYY-MM-DD
    title: str
    excerpt: str
    url: str
    tags: list[str] = field(default_factory=list)


def _strip(s: str | None) -> str:
    if not s:
        return ""
    return unescape(re.sub(r"<[^>]+>", " ", s)).strip()


def _fetch_tag_names(
    client: httpx.Client,
    tag_ids: list[int],
    per_page: int = 100,
) -> dict[int, str]:
    if not tag_ids:
        return {}
    r = client.get(
        WP_TAGS_API,
        params={
            "include": ",".join(str(i) for i in tag_ids),
            "per_page": per_page,
            "_fields": "id,name",
        },
        timeout=20,
    )
    r.raise_for_status()
    return {t["id"]: t["name"] for t in r.json()}


def fetch_statements(client: httpx.Client, per_page: int = 100) -> list[Statement]:
    r = client.get(
        WP_API,
        params={
            "artikkelin_tyyppi": 8,
            "per_page": per_page,
            "orderby": "date",
            "order": "desc",
            "_fields": "id,date,title,link,excerpt,tags",
        },
        timeout=20,
    )
    r.raise_for_status()
    raw = r.json()

    all_tag_ids = list({tag_id for post in raw for tag_id in post.get("tags", [])})
    tag_names = _fetch_tag_names(client, all_tag_ids)

    return [
        Statement(
            id=p["id"],
            date=p["date"][:10],
            title=_strip(p["title"]["rendered"]),
            excerpt=_strip(p.get("excerpt", {}).get("rendered", "")),
            url=p["link"],
            tags=[tag_names[t] for t in p.get("tags", []) if t in tag_names],
        )
        for p in raw
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
                "tags": s.tags,
            }
            for s in statements
        ],
    }
