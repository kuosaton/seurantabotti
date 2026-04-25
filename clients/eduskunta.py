from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import httpx

VASKI_URL = "https://avoindata.eduskunta.fi/api/v1/tables/VaskiData/rows"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; seurantabotti/1.0)"}

NS = {
    "vaski": "http://www.eduskunta.fi/skeemat/vaskikooste/2011/01/04",
    "meta": "http://www.vn.fi/skeemat/metatietoelementit/2010/04/27",
}

ITEM_RE = re.compile(
    r'\{edktunnus:"(?P<edktunnus>[^"]+)"'
    r',eduskuntatunnus:(?:null|"(?P<eduskuntatunnus>[^"]*)")'
    r',asiakirjatyyppinimi:"(?P<tyyppinimi>[^"]+)"'
    r',asiakirjatyyppikoodi:"(?P<tyyppikoodi>[^"]+)"'
    r'.*?nimeketeksti:"(?P<nimeke>[^"]+)"'
    r'.*?laadintapvm:"(?P<pvm>[^"]+)"'
    r'.*?viimeisinJulkaisuajankohta:"(?P<julkaistu>[^"]+)"',
)


@dataclass
class Document:
    """A document item embedded on a committee page (VS, esityslista, etc.)."""

    edktunnus: str
    eduskuntatunnus: str | None
    tyyppikoodi: str
    nimeke: str
    laadintapvm: str
    julkaistu: str


@dataclass
class Matter:
    """A single matter scheduled on a committee agenda."""

    eduskuntatunnus: str
    title: str
    type: str


def fetch_committee_page(client: httpx.Client, url: str) -> str:
    r = client.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def extract_documents(html: str) -> list[Document]:
    """Extract VS / KS / esityslista / pöytäkirja items from a committee page."""
    documents = []
    for m in ITEM_RE.finditer(html):
        documents.append(
            Document(
                edktunnus=m.group("edktunnus"),
                eduskuntatunnus=m.group("eduskuntatunnus"),
                tyyppikoodi=m.group("tyyppikoodi"),
                nimeke=m.group("nimeke"),
                laadintapvm=m.group("pvm"),
                julkaistu=m.group("julkaistu"),
            )
        )
    return documents


def fetch_agenda_xml(client: httpx.Client, eduskuntatunnus: str) -> str:
    """Fetch the latest version of a VaskiData document by parliamentary code."""
    r = client.get(
        VASKI_URL,
        params={
            "columnName": "Eduskuntatunnus",
            "columnValue": eduskuntatunnus,
            "page": "0",
            "perPage": "10",
        },
        headers=HEADERS,
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    rows = data.get("rowData") or []
    if not rows:
        raise LookupError(f"No VaskiData rows for {eduskuntatunnus!r}")
    cols = data["columnNames"]
    latest = max(rows, key=lambda row: dict(zip(cols, row, strict=True)).get("Created") or "")
    return dict(zip(cols, latest, strict=True))["XmlData"]


def parse_agenda_matters(xml: str) -> list[Matter]:
    """Extract matters being heard from an esityslista XML."""
    root = ET.fromstring(xml)
    matters = []
    for ak in root.iter(f"{{{NS['vaski']}}}Asiakohta"):
        tunnus = ak.findtext("vaski:KohtaAsia/meta:EduskuntaTunnus", namespaces=NS)
        if not tunnus:
            continue
        title = ak.findtext("vaski:KohtaNimeke/meta:NimekeTeksti", namespaces=NS) or ""
        type_name = ak.findtext("vaski:KohtaAsia/meta:AsiakirjatyyppiNimi", namespaces=NS) or ""
        matters.append(
            Matter(
                eduskuntatunnus=tunnus.strip(),
                title=title.strip(),
                type=type_name.strip(),
            )
        )
    return matters
