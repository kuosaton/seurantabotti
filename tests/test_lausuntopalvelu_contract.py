from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import clients.lausuntopalvelu as lapa

_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "lausuntopalvelu"


def test_fetch_recent_contract_against_recorded_feed_fixture() -> None:
    xml = (_FIXTURE_DIR / "proposals_feed.xml").read_text(encoding="utf-8")
    expected = json.loads(
        (_FIXTURE_DIR / "proposals_feed_expected.json").read_text(encoding="utf-8")
    )

    class FakeClient:
        def get(self, url, params, timeout):
            assert url.endswith("/Proposals")
            assert params["$orderby"] == "PublishedOn desc"
            assert params["$top"] == "2"
            assert timeout == 20
            return SimpleNamespace(text=xml, raise_for_status=lambda: None)

    items = lapa.fetch_recent(FakeClient(), top=2)
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
