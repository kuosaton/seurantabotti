# Seurantabotti, Technical Development Spec

## Design principle

High precision, tolerate false negatives. The customer gets formal hearing invitations through official channels regardless, so a missed item is not a critical failure. A spammy notification stream, however, destroys the tool's entire value proposition, which is to reduce information load.

Every design decision below flows from this principle.

## Project structure

```text
seurantabotti/
├── pyproject.toml
├── .env.example              # ANTHROPIC_API_KEY, SMTP credentials, recipient email
├── config.py                 # thresholds, committee list, schedule
├── main.py                   # CLI entrypoint: `python main.py --daily` / `--weekly`
│
├── clients/
│   ├── lausuntopalvelu.py    # OData/Atom XML client
│   ├── eduskunta.py          # committee page scraper + VaskiData client
│   └── kuluttajaliitto.py    # WordPress REST API client
│
├── processing/
│   ├── document_parser.py    # PDF/DOCX text extraction (Sprint 4)
│   └── llm_scorer.py         # Claude relevance scoring
│
├── delivery/
│   └── email.py              # SMTP sender with HTML templates
│
├── state/
│   ├── seen_proposals.json   # {proposal_id: {first_seen, score, notified}}
│   ├── seen_documents.json   # {document_id: {first_seen, score, notified}}
│   └── score_log.jsonl       # append-only: every scored item, for calibration
│
├── context/
│   └── kuluttajaliitto.json  # fetched focus areas, updated weekly
│
└── tests/
```

## Data sources: concrete API calls

### 1. Lausuntopalvelu.fi (OData/Atom XML)

Base URL: `https://www.lausuntopalvelu.fi/api/v1/Lausuntopalvelu.svc`

**The API returns Atom XML only.** `$format=json` causes HTTP 400. Parse responses with
`xml.etree.ElementTree`. OData query parameters work, but spaces in values must be
percent-encoded as `%20` (a literal space in the URL causes `InvalidURL` at the Python
`http.client` level).

Fetch recent proposals ordered by publication date:

```http
GET /Proposals?$orderby=PublishedOn%20desc&$top=50
```

Fetch single proposal with details:

```http
GET /Proposals(guid'{proposal_id}')
```

Fetch proposal attachments:

```http
GET /Proposals(guid'{proposal_id}')/Reports
```

XML namespaces needed for parsing:

```python
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "d": "http://schemas.microsoft.com/ado/2007/08/dataservices",
    "m": "http://schemas.microsoft.com/ado/2007/08/dataservices/metadata",
}
```

Each entry's fields are inside `<content type="application/xml"><m:properties>`. Verified
field names (prefixed with `d:` in the XML):

| XML field          | Dataclass field     | Notes                                                 |
| ------------------ | ------------------- | ----------------------------------------------------- |
| `Id`               | `id`                | GUID string                                           |
| `Name`             | `title`             | Finnish title                                         |
| `Goals`            | `abstract`          | May contain raw HTML `<span>` tags — strip before use |
| `Deadline`         | `deadline`          | ISO datetime string                                   |
| `PublishedOn`      | `published_on`      | Use for ordering and deduplication                    |
| `OrganizationName` | `organization_name` | e.g. "Työ- ja elinkeinoministeriö"                    |
| `RegisterNumber`   | `register_number`   | e.g. "VN/6671/2026", may be None                      |

Expected dataclass:

```python
@dataclass
class Proposal:
    id: str
    title: str
    organization_name: str
    abstract: str               # HTML stripped
    deadline: datetime
    published_on: datetime
    url: str                    # f"https://www.lausuntopalvelu.fi/FI/Proposal/Participation?proposalId={id}"
```

HTML stripping for the `Goals` field:

```python
import re
from html import unescape

def strip_html(s: str) -> str:
    return unescape(re.sub(r"<[^>]+>", " ", s or "")).strip()
```

Remaining unknown: rate limits are undocumented. Start at 1 req/s, back off on 429.

### 2. Eduskunta

#### Committee page scraping

The committee pages are server-rendered SPAs. Each committee's main page embeds the
relevant document lists as JavaScript object literals directly in the HTML — keys are
unquoted, so the content is **not valid JSON** and cannot be parsed with `json.loads`.
Use regex to extract the fields you need.

The pages are large (~3 MB). Fetch once per run and extract all needed data in one pass.

```python
COMMITTEE_URLS = {
    "talousvaliokunta": "https://www.eduskunta.fi/kansanedustajat-ja-toimielimet/valiokunnat/talousvaliokunta",
    "maa_ja_metsatalousvaliokunta": "https://www.eduskunta.fi/kansanedustajat-ja-toimielimet/valiokunnat/maa-ja-metsatalousvaliokunta",
    "ymparistovaliokunta": "https://www.eduskunta.fi/kansanedustajat-ja-toimielimet/valiokunnat/ymparistovaliokunta",
}
```

The embedded JS contains arrays named `valiokunnanViikkosuunnitelmat` (weekly schedules)
and `valiokunnanEsityslistat` (meeting agendas). Each item has these fields:

| Field                        | Example value                       | Notes                                              |
| ---------------------------- | ----------------------------------- | -------------------------------------------------- |
| `edktunnus`                  | `"EDK-2026-AK-2517"`                | Internal EDK identifier                            |
| `eduskuntatunnus`            | `"TaVE 37/2026 vp"`                 | Parliamentary document code, may be null for VS/KS |
| `asiakirjatyyppikoodi`       | `"TaVE"`                            | See document type codes below                      |
| `nimeketeksti`               | `"Keskiviikko 22.4.2026 klo 11.00"` | Human-readable title                               |
| `laadintapvm`                | `"2026-04-22"`                      | Date created/published                             |
| `htmlSaatavilla`             | `true`                              | Whether HTML content is available                  |
| `viimeisinJulkaisuajankohta` | `"2026-04-22T08:39:21.404+00:00"`   | Last published timestamp                           |

Document type codes:

| Code                     | Meaning                                                  |
| ------------------------ | -------------------------------------------------------- |
| `VS`                     | Viikkosuunnitelma — forward-looking weekly schedule      |
| `KS`                     | Kokoussuunnitelma — longer-range meeting plan            |
| `TaVE` / `MmVE` / `YmVE` | Esityslista — meeting agenda (lists matters to be heard) |
| `TaVP` / `MmVP` / `YmVP` | Pöytäkirja — meeting minutes (past meetings)             |
| `TaVM` / `MmVM` / `YmVM` | Mietintö — committee report                              |
| `TaVL` / `MmVL` / `YmVL` | Lausunto — committee statement                           |

Regex to extract document items from the embedded JS:

```python
ITEM_RE = re.compile(
    r'\{edktunnus:"(?P<edktunnus>[^"]+)"'
    r',eduskuntatunnus:(?:null|"(?P<eduskuntatunnus>[^"]*)")'
    r',asiakirjatyyppinimi:"(?P<tyyppinimi>[^"]+)"'
    r',asiakirjatyyppikoodi:"(?P<tyyppikoodi>[^"]+)"'
    r'.*?nimeketeksti:"(?P<nimeke>[^"]+)"'
    r'.*?laadintapvm:"(?P<pvm>[^"]+)"'
    r'.*?viimeisinJulkaisuajankohta:"(?P<julkaistu>[^"]+)"'
)
```

For weekly monitoring, filter to `VS` (new weekly plan) and `TaVE`/`MmVE`/`YmVE`
(upcoming meeting agendas). Ignore `TaVP`/`MmVP`/`YmVP` (past minutes).

#### VaskiData API — fetching agenda content

The VaskiData API provides the full XML content of published documents. Use it to get
the list of matters (HE XX/2026 vp, etc.) scheduled in an agenda.

Base URL: `https://avoindata.eduskunta.fi/api/v1`

Fetch a document by its exact parliamentary code:

```http
GET /tables/VaskiData/rows?columnName=Eduskuntatunnus&columnValue=TaVE%2037%2F2026%20vp&page=0&perPage=1
```

**Important**: the column is `Eduskuntatunnus`, not `Pitkätunnus` (which does not
exist). The filter requires an **exact full document code** — prefix-only values like
`TaVM` return zero rows.

Response shape:

```python
{
    "columnNames": ["Id", "XmlData", "Status", "Created", "Eduskuntatunnus", "AttachmentGroupId", "Imported"],
    "rowData": [
        [row_id, xml_string, status, created, eduskuntatunnus, attachment_group_id, imported]
    ],
    "hasMore": bool,
    ...
}
```

The `XmlData` column (index 1) contains the full document XML. For an esityslista,
parse out the matter references and their titles:

```python
import re

def parse_agenda_matters(xml: str) -> list[dict]:
    tunnus_re = re.compile(r"<[^:>]*:?EduskuntaTunnus[^>]*>([^<]+)</[^>]+>")
    nimeke_re = re.compile(r"<[^:>]*:?NimekeTeksti[^>]*>([^<]+)</[^>]+>")
    refs   = tunnus_re.findall(xml)
    titles = nimeke_re.findall(xml)
    # First title is the document's own title; subsequent ones are matter titles.
    # Pair refs[1:] with titles[1:] — index 0 is the esityslista itself.
    matters = []
    for ref, title in zip(refs, titles[1:]):
        if ref.startswith(("HE ", "LA ", "KA ", "VK ")):  # legislative matters
            matters.append({"eduskuntatunnus": ref, "title": title.strip()})
    return matters
```

Verified on TaVE 37/2026 vp (2026-04-22): refs found were `HE 24/2026 vp`,
`HE 22/2026 vp`, `HE 37/2026 vp` with their respective titles.

#### Pipeline summary for committee monitoring

```text
For each committee:
  1. GET committee main page HTML
  2. Regex-extract VS and TaVE/MmVE/YmVE items
  3. Filter to items not yet seen (by edktunnus)
  4. For each new esityslista:
       a. GET VaskiData by exact Eduskuntatunnus
       b. Parse XmlData for matter references + titles
       c. Score each matter via LLM
  5. Score new VS items (title + nimeke as abstract) via LLM
```

The `seen_documents.json` state file tracks items by `edktunnus`.

### 3. Kuluttajaliitto context

**Use the WordPress REST API — no HTML scraping needed.**

The `ajankohtaista/?3897474937=8` URL in the original spec is a Kadence Query block
widget parameter, not a WordPress category. Posts are standard WP `post` type, filtered
by tag. Tag 3606 = "lausunto" (199 posts as of 2026-04-22).

Fetch recent lausunnot:

```http
GET https://www.kuluttajaliitto.fi/wp-json/wp/v2/posts
    ?tags=3606
    &per_page=15
    &orderby=date
    &order=desc
    &_fields=id,date,title,link,excerpt
```

Response fields:

```python
post["title"]["rendered"]    # HTML — strip tags
post["excerpt"]["rendered"]  # HTML — strip tags
post["link"]                 # canonical URL
post["date"]                 # ISO 8601
```

Both `title` and `excerpt` are HTML-rendered — apply `strip_html()` before use.

Output written to `context/kuluttajaliitto.json`:

```python
{
    "last_updated": "2026-04-22",
    "recent_statements": [
        {
            "title": "Kirjallinen lausunto työ- ja elinkeinoministeriölle...",
            "date": "2026-03-30",
            "url": "https://www.kuluttajaliitto.fi/2026/03/30/...",
            "excerpt": "Kuluttajaliitto kiittää mahdollisuudesta antaa..."
        }
    ]
}
```

Refresh weekly (Sunday night). The fetched statements are the only relevance signal;
there is no static keyword list.

## Relevance scoring

### Single-stage LLM evaluation

```python
# llm_scorer.py

SYSTEM_PROMPT = """Olet Kuluttajaliiton avustaja, joka arvioi
lausuntopalvelu.fi:n lausuntopyyntöjen ja eduskunnan valiokunta-asioiden
relevanssia Kuluttajaliitolle.

Saat arvioitavaksi yhden asian otsikon ja kuvauksen. Saat myös
tausta-aineistona Kuluttajaliiton verkkosivujen ajankohtaiset painopisteet
sekä viimeisimmät julkaistut lausunnot.

Tehtäväsi:
1. Arvioi asteikolla 0-10, kuinka relevantti asia on Kuluttajaliitolle
2. Kirjoita 1-2 lauseen perustelu suomeksi. Viittaa tarvittaessa
   Kuluttajaliiton aiempiin lausuntoihin tai painopisteisiin.
3. Nimeä 1-3 asian keskeistä teemaa

Vastaa AINOASTAAN JSON-muodossa, ilman muuta tekstiä:
{
    "score": 7,
    "rationale": "Koskee verkkokaupan kuluttajansuojaa EU-direktiivin toimeenpanossa. Kuluttajaliitto on antanut aiheesta lausuntoja aiemmin.",
    "themes": ["verkkokauppa", "kuluttajansuoja", "EU-direktiivi"]
}

Pisteytysohje:
- 8-10: Asia on selvästi Kuluttajaliiton ydinaluetta. Liittyy suoraan
  kuluttajansuojaan, tuoteturvallisuuteen, rahoituspalveluihin, asumiseen
  tai muuhun aiheeseen, josta Kuluttajaliitto on toistuvasti lausunut.
- 5-7: Asia koskee kuluttajia epäsuorasti tai sivuaa Kuluttajaliiton
  painopisteitä, mutta ei ole ydinaluetta.
- 2-4: Asialla on ohut yhteys kuluttaja-asioihin.
- 0-1: Ei havaittavaa yhteyttä kuluttajiin tai Kuluttajaliiton toimintaan.

TÄRKEÄ OHJE: Epävarmoissa tapauksissa anna mieluummin matalampi kuin
korkeampi pistemäärä. Kuluttajaliitto saa kutsut kuulemisiin joka
tapauksessa virallisia kanavia pitkin, joten yksittäisen asian nostamatta
jääminen ei ole kriittistä. Sen sijaan väärät nostot heikentävät työkalun
käyttökelpoisuutta. Nosta vain, jos asia on selvästi relevantti."""
```

User prompt:

```python
def build_user_prompt(
    item_title: str,
    item_abstract: str,
    item_source: str,  # "lausuntopalvelu" or "talousvaliokunta" etc.
    kuluttajaliitto_context: dict,
) -> str:
    statements = "\n".join(
        f"- {s['date']}: {s['title']}\n  {s['excerpt']}"
        for s in kuluttajaliitto_context["recent_statements"][:15]
    )
    return f"""## Arvioitava asia

**Lähde:** {item_source}
**Otsikko:** {item_title}
**Kuvaus:** {item_abstract}

## Kuluttajaliiton viimeaikaiset lausunnot

{statements}
"""
```

API call:

```python
import anthropic

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=300,
    system=SYSTEM_PROMPT,
    messages=[{"role": "user", "content": user_prompt}],
)

result = json.loads(response.content[0].text)
```

Cost estimate: roughly 800 input tokens plus 100 output per item. Realistic volumes: 10–20
lausuntopalvelu items/day, ~30 committee matters/week across three committees — roughly
140 items/week, around $0.42/week at Sonnet pricing.

### Thresholds

```python
# config.py
NOTIFY_THRESHOLD = 7       # score >= 7 triggers email
LOG_THRESHOLD = 4          # score 4-6 logged for later review
# score 0-3 silently dropped
```

All scored items append to `score_log.jsonl` regardless of score. Review the 4–6 band
periodically to calibrate the threshold.

## Email delivery

### SMTP setup

Start with Gmail SMTP + app password. Migrate to Resend/SES later if deliverability
or multi-recipient support becomes a concern.

```python
# delivery/email.py

import os, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_email(
    to: str,
    subject: str,
    html_body: str,
    text_body: str,
    smtp_host: str = "smtp.gmail.com",
    smtp_port: int = 587,
    smtp_user: str = os.environ["SMTP_USER"],
    smtp_pass: str = os.environ["SMTP_PASS"],
):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
```

### Email templates

Weekly digest (Fridays):

```text
Subject: Seurantabotti viikkokatsaus, vko {week_number}

{greeting}

--- TALOUSVALIOKUNTA ---

{for each flagged item:}
▸ {title}
   Käsittely: {date}
   Relevanssi: {score}/10
   {rationale}
   Linkki: {url}

--- MAA- JA METSÄTALOUSVALIOKUNTA ---

{...}

--- YMPÄRISTÖVALIOKUNTA ---

{...}

---

Arvioitu yhteensä: {total_scored} asiaa
Nostettu: {total_notified}
Lokitettu (pistemäärä 4-6): {total_logged}
```

Daily lausuntopalvelu digest (only sent when flagged items exist):

```text
Subject: Uusia lausuntopyyntöjä, {date}

{count} uutta lausuntopyyntöä, jotka saattavat kiinnostaa:

{for each flagged item:}
▸ {title}
   Pyytäjä: {organization}
   Määräaika: {deadline}
   Relevanssi: {score}/10
   {rationale}
   Linkki: {url}
```

Provide both HTML and plain-text versions. Keep the HTML simple: inline CSS, no images,
no tracking pixels.

## State management

```python
# state/seen_proposals.json
{
    "a0b64d61-da0b-46c3-8676-e3b1f0a76c5f": {
        "first_seen": "2026-04-10T08:15:00Z",
        "title": "Lausuntopyyntö...",
        "score": 7,
        "notified": true,
        "notified_at": "2026-04-10T08:16:00Z"
    }
}
```

```python
# state/seen_documents.json — keyed by edktunnus
{
    "EDK-2026-AK-2517": {
        "first_seen": "2026-04-22T08:00:00Z",
        "eduskuntatunnus": "TaVE 37/2026 vp",
        "nimeke": "Keskiviikko 22.4.2026 klo 11.00",
        "score": null,           # null for container docs (VS, esityslista)
        "matter_scores": {
            "HE 24/2026 vp": {"score": 3, "notified": false},
            "HE 22/2026 vp": {"score": 8, "notified": true}
        }
    }
}
```

```python
# state/score_log.jsonl (append-only, one JSON object per line)
{"timestamp": "2026-04-10T08:15:00Z", "source": "lausuntopalvelu", "id": "...", "title": "...", "score": 5, "rationale": "...", "themes": [...], "notified": false}
```

Per-run flow:

1. Fetch latest items from source
2. Filter out already-seen IDs
3. Score new items via LLM
4. Append all results to `score_log.jsonl`
5. Items with `score >= NOTIFY_THRESHOLD` queued for email
6. Update `seen_proposals.json` / `seen_documents.json`
7. If queue non-empty, send email

## CLI entrypoint

```python
# main.py

def main():
    parser = argparse.ArgumentParser(description="Seurantabotti")
    parser.add_argument("--daily", action="store_true",
                        help="Run daily lausuntopalvelu check")
    parser.add_argument("--weekly", action="store_true",
                        help="Run weekly committee digest (Fridays)")
    parser.add_argument("--midweek", action="store_true",
                        help="Run mid-week committee update check (higher threshold)")
    parser.add_argument("--update-context", action="store_true",
                        help="Refresh Kuluttajaliitto context from their website")
    parser.add_argument("--dry-run", action="store_true",
                        help="Score items and log them but don't send email")
    parser.add_argument("--review-logged", action="store_true",
                        help="Print items scored 4-6 from the last N days for calibration review")
    args = parser.parse_args()
    ...
```

Cron setup:

```cron
# Daily lausuntopalvelu check at 08:00
0 8 * * * cd /path/to/seurantabotti && python main.py --daily

# Weekly committee digest on Fridays at 16:00 (after schedules drop)
0 16 * * 5 cd /path/to/seurantabotti && python main.py --weekly

# Mid-week committee check Tuesday/Wednesday mornings
0 9 * * 2,3 cd /path/to/seurantabotti && python main.py --midweek

# Refresh Kuluttajaliitto context on Sundays at 22:00
0 22 * * 0 cd /path/to/seurantabotti && python main.py --update-context
```

## Dependencies

```toml
[project]
name = "seurantabotti"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "httpx>=0.27",
    "anthropic>=0.40",
]

[project.optional-dependencies]
v4 = [
    "pymupdf>=1.24",           # PDF extraction (Sprint 4)
    "python-docx>=1.1",        # DOCX extraction (Sprint 4)
]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "ruff>=0.8",
]
```

XML parsing uses `xml.etree.ElementTree` (stdlib). HTML stripping uses `re` (stdlib).
SMTP uses `smtplib` (stdlib). `beautifulsoup4` and `lxml` are no longer needed: the
lausuntopalvelu XML is well-formed enough for ElementTree, and kuluttajaliitto switched
from HTML scraping to the REST API.

## Build order

### Sprint 1: lausuntopalvelu end-to-end (day 1)

1. Project skeleton: `pyproject.toml`, `.env.example`, `config.py`
2. `clients/lausuntopalvelu.py`: Atom XML fetch and parse; `Proposal` dataclass; `strip_html()` for Goals field
3. `state/` read/write for `seen_proposals.json` and `score_log.jsonl`
4. `clients/kuluttajaliitto.py`: WP REST API fetch (tag=3606), produce `context/kuluttajaliitto.json`
5. `processing/llm_scorer.py`: with the prompt above
6. `delivery/email.py`: SMTP sending, both template versions
7. `main.py --daily --dry-run` works end-to-end
8. `main.py --daily` sends real email

### Sprint 2: committee monitoring (day 2)

1. `clients/eduskunta.py`:
   - Fetch committee main page HTML
   - Regex-extract VS and esityslista items from embedded JS
   - Fetch esityslista XML from VaskiData by exact Eduskuntatunnus
   - Parse matter references (HE/LA/etc.) from XML
2. `state/seen_documents.json` read/write
3. Plug into existing scorer and email pipeline — cover all three committees
4. `main.py --weekly` works

### Sprint 3: automated context refresh (day 3)

1. `main.py --update-context` calls `clients/kuluttajaliitto.py` and writes fresh JSON
2. Verify LLM quality with dynamically-refreshed context vs. stale context

### Sprint 4: attachment processing and calibration (day 4+)

1. Download and extract text from PDF/DOCX attachments for lausuntopalvelu proposals
2. Include attachment excerpts in LLM prompt for borderline cases
3. `main.py --review-logged`: print recent score-4–6 items for manual threshold review
4. Adjust `NOTIFY_THRESHOLD` if needed

### Sprint 5: hardening

1. Proper error handling (HTTP failures, malformed XML, LLM JSON parse errors)
2. Structured logging
3. Retry with exponential backoff
4. State file atomic writes (write to `.tmp`, rename)
5. Deploy to cron, GitHub Actions, or Hetzner VPS

## Remaining unknowns

All Sprint 1 and Sprint 2 API-format blockers are now resolved. The following are still
open:

1. **Lausuntopalvelu rate limits**: undocumented. Start at 1 req/s, back off on 429.
2. **Attachment download URLs**: do lausuntopalvelu `/Reports` links point to directly
   downloadable files, or is auth/session required? Investigate in Sprint 4.
3. **MmV and YmV page structure**: assumed identical to TaV based on consistent site
   design. Verify the regex works against live MmV and YmV pages before Sprint 2 is
   marked done.
4. **VaskiData `hasMore` on esityslista**: TaVE 37/2026 vp returned `hasMore: true`
   with `perPage=1`. This likely means multiple versions (drafts + approved). Always
   fetch the latest version — use `page=0&perPage=1` after ordering by `Created` desc,
   or fetch all versions and take the most recent `Created` timestamp.

---

_Last updated 22.4.2026. Version 1.2._
