from __future__ import annotations

from types import SimpleNamespace

import clients.kuluttajaliitto as kk


def test_strip_handles_html_and_none() -> None:
    assert kk._strip(None) == ""
    assert kk._strip("<p>Hei &amp; moi</p>") == "Hei & moi"


def test_fetch_statements_parses_wp_response() -> None:
    payload = [
        {
            "id": 123,
            "date": "2026-04-20T10:30:00",
            "title": {"rendered": "<strong>Lausunto</strong>"},
            "excerpt": {"rendered": "<p>Tiivistelma &amp; huomio</p>"},
            "link": "https://example.invalid/lausunto-1",
        }
    ]

    class FakeClient:
        def get(self, url, params, timeout):
            assert url == kk.WP_API
            assert params["tags"] == kk.LAUSUNTO_TAG_ID
            assert params["per_page"] == 10
            assert timeout == 20
            return SimpleNamespace(
                raise_for_status=lambda: None,
                json=lambda: payload,
            )

    items = kk.fetch_statements(FakeClient(), per_page=10)
    assert len(items) == 1
    assert items[0].id == 123
    assert items[0].date == "2026-04-20"
    assert items[0].title == "Lausunto"
    assert items[0].excerpt == "Tiivistelma & huomio"


def test_build_context_maps_statements() -> None:
    statements = [
        kk.Statement(
            id=1,
            date="2026-04-21",
            title="T1",
            excerpt="E1",
            url="https://example.invalid/1",
        )
    ]
    ctx = kk.build_context(statements)
    assert "last_updated" in ctx
    assert ctx["recent_statements"][0]["title"] == "T1"
    assert ctx["recent_statements"][0]["excerpt"] == "E1"
