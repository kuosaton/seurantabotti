from __future__ import annotations

from datetime import datetime

import httpx

import clients.lausuntopalvelu as lapa


def test_strip_html_none_returns_empty() -> None:
    assert lapa.strip_html(None) == ""


def test_parse_dt_valid_and_invalid() -> None:
    assert lapa._parse_dt("2026-04-22T10:52:41.58") == datetime(2026, 4, 22, 10, 52, 41)
    assert lapa._parse_dt("2026-04-22T10:52:41.58Z") == datetime(2026, 4, 22, 10, 52, 41)
    assert lapa._parse_dt("not-a-date") is None
    assert lapa._parse_dt(None) is None


def test_fetch_recent_parses_atom_feed() -> None:
    xml = """<?xml version="1.0" encoding="utf-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom"
          xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices"
          xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata">
      <entry>
        <content type="application/xml">
          <m:properties>
            <d:Id>abc-123</d:Id>
            <d:Name>Otsikko</d:Name>
            <d:Goals>&lt;p&gt;Kuvaus&lt;/p&gt;</d:Goals>
            <d:Deadline>2026-05-01T00:00:00</d:Deadline>
            <d:PublishedOn>2026-04-21T10:56:55.763</d:PublishedOn>
            <d:OrganizationName>Ministerio</d:OrganizationName>
          </m:properties>
        </content>
      </entry>
    </feed>
    """

    class _Transport(httpx.BaseTransport):
        def handle_request(self, request: httpx.Request) -> httpx.Response:
            assert str(request.url).split("?")[0].endswith("/Proposals")
            assert request.url.params["$top"] == "1"
            return httpx.Response(200, text=xml)

    with httpx.Client(transport=_Transport()) as client:
        items = lapa.fetch_recent(client, top=1)
    assert len(items) == 1
    p = items[0]
    assert p.id == "abc-123"
    assert p.title == "Otsikko"
    assert p.abstract == "Kuvaus"
    assert p.organization_name == "Ministerio"
    assert p.deadline == datetime(2026, 5, 1, 0, 0, 0)
    assert p.url.endswith("proposalId=abc-123")
