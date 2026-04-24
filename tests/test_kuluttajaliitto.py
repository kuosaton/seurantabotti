from __future__ import annotations

from types import SimpleNamespace

import clients.kuluttajaliitto as kk


def test_strip_handles_html_and_none() -> None:
    assert kk._strip(None) == ""
    assert kk._strip("<p>Hei &amp; moi</p>") == "Hei & moi"


def test_fetch_statements_parses_wp_response() -> None:
    posts_payload = [
        {
            "id": 123,
            "date": "2026-04-20T10:30:00",
            "title": {"rendered": "<strong>Lausunto</strong>"},
            "excerpt": {"rendered": "<p>Tiivistelma &amp; huomio</p>"},
            "link": "https://example.invalid/lausunto-1",
            "tags": [3606, 9999],
        }
    ]
    tags_payload = [
        {"id": 3606, "name": "lausunto"},
        {"id": 9999, "name": "kuluttajansuoja"},
    ]

    calls = []

    class FakeClient:
        def get(self, url, params, timeout):
            calls.append(url)
            if url == kk.WP_API:
                assert params["artikkelin_tyyppi"] == 8
                assert params["per_page"] == 10
                assert timeout == 20
                return SimpleNamespace(raise_for_status=lambda: None, json=lambda: posts_payload)
            if url == kk.WP_TAGS_API:
                return SimpleNamespace(raise_for_status=lambda: None, json=lambda: tags_payload)

    items = kk.fetch_statements(FakeClient(), per_page=10)
    assert len(items) == 1
    assert items[0].id == 123
    assert items[0].date == "2026-04-20"
    assert items[0].title == "Lausunto"
    assert items[0].excerpt == "Tiivistelma & huomio"
    assert set(items[0].tags) == {"lausunto", "kuluttajansuoja"}
    assert kk.WP_TAGS_API in calls


def test_build_context_maps_statements() -> None:
    statements = [
        kk.Statement(
            id=1,
            date="2026-04-21",
            title="T1",
            excerpt="E1",
            url="https://example.invalid/1",
            tags=["lausunto", "asuminen"],
        )
    ]
    ctx = kk.build_context(statements)
    assert "last_updated" in ctx
    assert ctx["recent_statements"][0]["title"] == "T1"
    assert ctx["recent_statements"][0]["excerpt"] == "E1"
    assert ctx["recent_statements"][0]["tags"] == ["lausunto", "asuminen"]
