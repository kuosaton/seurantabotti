from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from html import unescape

import httpx

BASE_URL = "https://www.lausuntopalvelu.fi/api/v1/Lausuntopalvelu.svc"
PROPOSAL_URL = "https://www.lausuntopalvelu.fi/FI/Proposal/Participation?proposalId={id}"

# Atom + OData namespaces
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "d": "http://schemas.microsoft.com/ado/2007/08/dataservices",
    "m": "http://schemas.microsoft.com/ado/2007/08/dataservices/metadata",
}


@dataclass
class Proposal:
    id: str
    title: str
    organization_name: str
    abstract: str
    deadline: datetime | None
    published_on: datetime
    url: str


def strip_html(s: str | None) -> str:
    if not s:
        return ""
    return unescape(re.sub(r"<[^>]+>", " ", s)).strip()


def _parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        # Values like "2026-04-22T10:52:41.58" or "2026-04-22T10:52:41.58Z"
        return datetime.fromisoformat(s.rstrip("Z").split(".")[0])
    except ValueError:
        return None


def _get(props: ET.Element | None, field: str) -> str | None:
    if props is None:
        return None
    el = props.find(f"d:{field}", NS)
    return el.text if el is not None else None


def _parse_entry(entry: ET.Element) -> Proposal:
    props = entry.find("atom:content/m:properties", NS)
    id_ = _get(props, "Id") or ""
    return Proposal(
        id=id_,
        title=strip_html(_get(props, "Name")),
        organization_name=_get(props, "OrganizationName") or "",
        abstract=strip_html(_get(props, "Goals")),
        deadline=_parse_dt(_get(props, "Deadline")),
        published_on=_parse_dt(_get(props, "PublishedOn")) or datetime.min,
        url=PROPOSAL_URL.format(id=id_),
    )


def fetch_recent(client: httpx.Client, top: int = 50) -> list[Proposal]:
    """Fetch the most recently published proposals, newest first."""
    r = client.get(
        f"{BASE_URL}/Proposals",
        params={"$orderby": "PublishedOn desc", "$top": str(top)},
        timeout=20,
    )
    r.raise_for_status()
    root = ET.fromstring(r.text)
    return [_parse_entry(e) for e in root.findall("atom:entry", NS)]


def proposal_has_recipient(
    client: httpx.Client,
    proposal_id: str,
    recipient_name: str,
) -> bool:
    """
    Return True when the proposal participation page's Jakelu table contains
    `recipient_name`.

    This uses the public Participation page because the OData API does not expose
    organization names for proposal participants.
    """
    url = PROPOSAL_URL.format(id=proposal_id)
    r = client.get(url, timeout=20)
    r.raise_for_status()
    html = r.text

    # Prefer the explicit Jakelu table when available.
    m = re.search(
        r"<h5>\s*Jakelu:\s*</h5>\s*<div[^>]*>\s*<table[^>]*>(?P<table>.*?)</table>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if m:
        return recipient_name.casefold() in strip_html(m.group("table")).casefold()

    # Fallback: scan only the Jakelu accordion region to avoid false positives.
    marker = "listOfRespondentsSettingsBody"
    idx = html.find(marker)
    if idx == -1:
        return False
    section = html[idx : idx + 50000]
    return recipient_name.casefold() in strip_html(section).casefold()
