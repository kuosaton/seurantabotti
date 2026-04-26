from __future__ import annotations

import json
from pathlib import Path

import httpx

import clients.lausuntopalvelu as lapa

_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "lausuntopalvelu"


def test_fetch_recent_contract_against_recorded_feed_fixture() -> None:
    xml = (_FIXTURE_DIR / "proposals_feed.xml").read_text(encoding="utf-8")
    expected = json.loads(
        (_FIXTURE_DIR / "proposals_feed_expected.json").read_text(encoding="utf-8")
    )

    class _Transport(httpx.BaseTransport):
        def handle_request(self, request: httpx.Request) -> httpx.Response:
            assert str(request.url).split("?")[0].endswith("/Proposals")
            assert request.url.params["$orderby"] == "PublishedOn desc"
            assert request.url.params["$top"] == "2"
            assert request.extensions["timeout"]["read"] == 20.0
            return httpx.Response(200, text=xml)

    with httpx.Client(transport=_Transport()) as client:
        items = lapa.fetch_recent(client, top=2)
    serialized = [
        {
            "id": p.id,
            "title": p.title,
            "organization_name": p.organization_name,
            "abstract": p.abstract,
            "deadline": p.deadline.isoformat() if p.deadline else None,
            "published_on": p.published_on.isoformat(),
            "url": p.url,
        }
        for p in items
    ]

    assert serialized == expected
