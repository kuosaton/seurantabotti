from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from clients.eduskunta import (
    HEADERS,
    VASKI_URL,
    extract_documents,
    fetch_agenda_xml,
    fetch_committee_page,
    parse_agenda_matters,
)

FIXTURES = Path(__file__).parent / "fixtures" / "eduskunta"


def test_extract_documents_finds_all_type_codes() -> None:
    html = (FIXTURES / "talousvaliokunta.html").read_text(encoding="utf-8")
    docs = extract_documents(html)

    assert len(docs) >= 5
    type_codes = {d.tyyppikoodi for d in docs}
    assert {"VS", "KS", "TaVE", "TaVP"}.issubset(type_codes)


def test_extract_documents_parses_esityslista_fields() -> None:
    html = (FIXTURES / "talousvaliokunta.html").read_text(encoding="utf-8")
    docs = extract_documents(html)

    esityslistat = [d for d in docs if d.tyyppikoodi == "TaVE"]
    assert esityslistat, "captured fixture should contain at least one TaVE"
    sample = esityslistat[0]
    assert sample.edktunnus.startswith("EDK-")
    assert sample.eduskuntatunnus and sample.eduskuntatunnus.startswith("TaVE ")
    assert sample.laadintapvm.count("-") == 2  # YYYY-MM-DD


def test_extract_documents_handles_null_eduskuntatunnus_for_vs() -> None:
    html = (FIXTURES / "talousvaliokunta.html").read_text(encoding="utf-8")
    docs = extract_documents(html)

    vs_items = [d for d in docs if d.tyyppikoodi == "VS"]
    assert vs_items, "captured fixture should contain at least one VS"
    assert all(v.eduskuntatunnus is None for v in vs_items)


def test_parse_agenda_matters_returns_real_matters_only() -> None:
    xml = (FIXTURES / "tave_40_2026_vp.xml").read_text(encoding="utf-8")
    matters = parse_agenda_matters(xml)

    tunnukset = [m.eduskuntatunnus for m in matters]
    assert tunnukset == [
        "HE 37/2026 vp",
        "U 27/2026 vp",
        "HE 2/2026 vp",
        "HE 24/2026 vp",
        "HE 44/2026 vp",
    ]


def test_parse_agenda_matters_includes_titles_and_types() -> None:
    xml = (FIXTURES / "tave_40_2026_vp.xml").read_text(encoding="utf-8")
    matters = parse_agenda_matters(xml)

    assert all(m.title for m in matters), "every matter should have a non-empty title"
    types = {m.type for m in matters}
    assert "Hallituksen esitys" in types
    assert "Valtioneuvoston U-kirjelmä" in types


def test_parse_agenda_matters_skips_referenced_statements() -> None:
    """MmVL/PeVL/HaVL/StVL refs in KohtaAsiakirja/MuuViite should not appear as matters."""
    xml = (FIXTURES / "tave_40_2026_vp.xml").read_text(encoding="utf-8")
    matters = parse_agenda_matters(xml)

    tunnukset = [m.eduskuntatunnus for m in matters]
    for tunnus in tunnukset:
        prefix = tunnus.split(" ", 1)[0]
        assert prefix not in {"MmVL", "PeVL", "HaVL", "StVL", "TaVL", "YmVL"}


def test_fetch_committee_page_sends_browser_user_agent() -> None:
    class _Transport(httpx.BaseTransport):
        def handle_request(self, request: httpx.Request) -> httpx.Response:
            assert str(request.url) == "https://example.invalid/tav"
            assert request.headers["user-agent"] == HEADERS["User-Agent"]
            return httpx.Response(200, text="<html>ok</html>")

    with httpx.Client(transport=_Transport()) as client:
        body = fetch_committee_page(client, "https://example.invalid/tav")
    assert body == "<html>ok</html>"
    assert "Mozilla" in HEADERS["User-Agent"]


def test_fetch_agenda_xml_picks_latest_by_created() -> None:
    response = {
        "columnNames": ["Id", "XmlData", "Created", "Eduskuntatunnus"],
        "rowData": [
            [1, "<old/>", "2026-04-20 10:00:00", "TaVE 1/2026 vp"],
            [2, "<latest/>", "2026-04-22 09:30:00", "TaVE 1/2026 vp"],
            [3, "<middle/>", "2026-04-21 14:00:00", "TaVE 1/2026 vp"],
        ],
        "hasMore": False,
    }

    class _Transport(httpx.BaseTransport):
        def handle_request(self, request: httpx.Request) -> httpx.Response:
            assert str(request.url).split("?")[0] == VASKI_URL
            assert request.url.params["columnName"] == "Eduskuntatunnus"
            assert request.url.params["columnValue"] == "TaVE 1/2026 vp"
            assert request.headers["user-agent"] == HEADERS["User-Agent"]
            return httpx.Response(200, json=response)

    with httpx.Client(transport=_Transport()) as client:
        xml = fetch_agenda_xml(client, "TaVE 1/2026 vp")
    assert xml == "<latest/>"


def test_fetch_agenda_xml_raises_on_empty_rows() -> None:
    response = {"columnNames": ["Id", "XmlData", "Created", "Eduskuntatunnus"], "rowData": []}

    class _Transport(httpx.BaseTransport):
        def handle_request(self, _request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=response)

    with httpx.Client(transport=_Transport()) as client:
        with pytest.raises(LookupError, match="No VaskiData rows"):
            fetch_agenda_xml(client, "TaVE 999/2026 vp")
