from __future__ import annotations

import functools
import json

import anthropic


@functools.lru_cache(maxsize=1)
def _get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


SYSTEM_PROMPT = """\
Olet Kuluttajaliiton avustaja, joka arvioi lausuntopalvelu.fi:n lausuntopyyntöjen \
ja eduskunnan valiokunta-asioiden relevanssia Kuluttajaliitolle.

Saat arvioitavaksi yhden asian otsikon ja kuvauksen. Saat myös tausta-aineistona \
Kuluttajaliiton verkkosivujen viimeisimmät julkaistut lausunnot.

Tehtäväsi:
1. Arvioi asteikolla 0-10, kuinka relevantti asia on Kuluttajaliitolle
2. Kirjoita 1-2 lauseen perustelu suomeksi. Viittaa tarvittaessa Kuluttajaliiton \
aiempiin lausuntoihin tai painopisteisiin.
3. Nimeä 1-3 asian keskeistä teemaa

Vastaa AINOASTAAN JSON-muodossa, ilman muuta tekstiä:
{"score": 7, "rationale": "Koskee verkkokaupan kuluttajansuojaa EU-direktiivin \
toimeenpanossa. Kuluttajaliitto on antanut aiheesta lausuntoja aiemmin.", \
"themes": ["verkkokauppa", "kuluttajansuoja", "EU-direktiivi"]}

Pisteytysohje:
- 8-10: Asia on selvästi Kuluttajaliiton ydinaluetta. Liittyy suoraan \
kuluttajansuojaan, tuoteturvallisuuteen, rahoituspalveluihin, asumiseen tai muuhun \
aiheeseen, josta Kuluttajaliitto on toistuvasti lausunut.
- 5-7: Asia koskee kuluttajia epäsuorasti tai sivuaa Kuluttajaliiton painopisteitä, \
mutta ei ole ydinaluetta.
- 2-4: Asialla on ohut yhteys kuluttaja-asioihin.
- 0-1: Ei havaittavaa yhteyttä kuluttajiin tai Kuluttajaliiton toimintaan.

TÄRKEÄ OHJE: Epävarmoissa tapauksissa anna mieluummin matalampi kuin korkeampi \
pistemäärä. Kuluttajaliitto saa kutsut kuulemisiin joka tapauksessa virallisia \
kanavia pitkin, joten yksittäisen asian nostamatta jääminen ei ole kriittistä. \
Sen sijaan väärät nostot heikentävät työkalun käyttökelpoisuutta. Nosta vain, jos \
asia on selvästi relevantti.\
"""


def _format_statements(statements: list[dict]) -> str:
    lines = []
    for s in statements:
        lines.append(f"- {s['date']}: {s['title']}")
        if s.get("tags"):
            lines.append(f"  Teemat: {', '.join(s['tags'])}")
        if s.get("excerpt"):
            lines.append(f"  {s['excerpt'][:450]}")
    return "\n".join(lines)


def score_item(
    title: str,
    abstract: str,
    source: str,
    context: dict,
    signals: dict | None = None,
) -> dict:
    """
    Score one item for relevance to Kuluttajaliitto.

    Returns {"score": int, "rationale": str, "themes": list[str]}.

    The system prompt and context block are marked for prompt caching — they stay
    identical across all calls in one run, so subsequent calls hit the cache.
    """
    context_text = _format_statements(context.get("recent_statements", []))
    signal_text = ""
    if signals and signals.get("jakelu_kuluttajaliitto"):
        signal_text = "\n**Lisäsignaali:** Jakelu-listassa on Kuluttajaliitto ry."
    item_text = (
        f"## Arvioitava asia\n\n"
        f"**Lähde:** {source}\n"
        f"**Otsikko:** {title}\n"
        f"**Kuvaus:** {abstract}"
        f"{signal_text}"
    )

    response = _get_client().messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"## Kuluttajaliiton viimeaikaiset lausunnot\n\n{context_text}",
                        "cache_control": {"type": "ephemeral"},
                    },
                    {
                        "type": "text",
                        "text": item_text,
                    },
                ],
            }
        ],
    )

    return json.loads(response.content[0].text)
