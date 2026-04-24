from __future__ import annotations

import functools
import json
import re

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


def _parse_response_json(raw_text: str) -> dict:
    text = raw_text.strip()
    candidates: list[str] = [text] if text else []

    # Accept fenced JSON outputs like ```json {...}```.
    for m in re.finditer(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.IGNORECASE | re.DOTALL):
        fenced = m.group(1).strip()
        if fenced:
            candidates.append(fenced)

    # Fallback: take the first balanced JSON object from surrounding prose.
    start = text.find("{")
    if start != -1:
        depth = 0
        for idx in range(start, len(text)):
            ch = text[idx]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidates.append(text[start : idx + 1])
                    break

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed

    preview = text[:180].replace("\n", "\\n")
    raise ValueError(f"Model response was not valid JSON object: {preview!r}")


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
    item_text = (
        f"## Arvioitava asia\n\n**Lähde:** {source}\n**Otsikko:** {title}\n**Kuvaus:** {abstract}"
    )

    response = _get_client().messages.create(
        model="claude-haiku-4-5",
        max_tokens=300,
        timeout=45.0,
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

    text_parts: list[str] = []
    for block in response.content:
        block_type = getattr(block, "type", None)
        text = getattr(block, "text", None)
        if block_type in (None, "text") and isinstance(text, str) and text.strip():
            text_parts.append(text)

    if not text_parts:
        raise ValueError("Anthropic response did not contain a non-empty text payload")

    return _parse_response_json("\n".join(text_parts))
