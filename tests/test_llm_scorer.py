from __future__ import annotations

from types import SimpleNamespace

import pytest

from processing import llm_scorer


def test_format_statements_includes_excerpt_when_present() -> None:
    text = llm_scorer._format_statements(
        [
            {"date": "2026-04-22", "title": "T1", "excerpt": "E1"},
            {"date": "2026-04-21", "title": "T2"},
        ]
    )

    assert "- 2026-04-22: T1" in text
    assert "E1" in text
    assert "- 2026-04-21: T2" in text


def test_format_statements_includes_tags_when_present() -> None:
    text = llm_scorer._format_statements(
        [{"date": "2026-04-22", "title": "T1", "tags": ["asuminen", "energia"]}]
    )

    assert "Teemat: asuminen, energia" in text


def test_score_item_ignores_jakelu_signal(monkeypatch) -> None:
    captured: dict = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            content=[
                SimpleNamespace(text='{"score": 6, "rationale": "ok", "themes": ["asuminen"]}')
            ]
        )

    fake_client = SimpleNamespace(messages=SimpleNamespace(create=fake_create))
    monkeypatch.setattr(llm_scorer, "_get_client", lambda: fake_client)

    result = llm_scorer.score_item(
        title="Testiotsikko",
        abstract="Testikuvaus",
        source="lausuntopalvelu",
        context={"recent_statements": []},
        signals={"jakelu_kuluttajaliitto": True},
    )

    user_content_blocks = captured["messages"][0]["content"]
    item_text = user_content_blocks[1]["text"]

    assert "Lisa" not in item_text
    assert "Lisäsignaali" not in item_text
    assert "Kuluttajaliitto ry" not in item_text
    assert result["score"] == 6


def test_score_item_parses_json_inside_markdown_fence(monkeypatch) -> None:
    def fake_create(**kwargs):
        return SimpleNamespace(
            content=[
                SimpleNamespace(
                    text=('```json\n{"score": 5, "rationale": "ok", "themes": ["teema"]}\n```')
                )
            ]
        )

    fake_client = SimpleNamespace(messages=SimpleNamespace(create=fake_create))
    monkeypatch.setattr(llm_scorer, "_get_client", lambda: fake_client)

    result = llm_scorer.score_item(
        title="A",
        abstract="B",
        source="lausuntopalvelu",
        context={"recent_statements": []},
    )

    assert result["score"] == 5
    assert result["themes"] == ["teema"]


def test_score_item_raises_on_empty_payload(monkeypatch) -> None:
    def fake_create(**kwargs):
        return SimpleNamespace(content=[SimpleNamespace(text="   ")])

    fake_client = SimpleNamespace(messages=SimpleNamespace(create=fake_create))
    monkeypatch.setattr(llm_scorer, "_get_client", lambda: fake_client)

    with pytest.raises(ValueError, match="non-empty text payload"):
        llm_scorer.score_item(
            title="A",
            abstract="B",
            source="lausuntopalvelu",
            context={"recent_statements": []},
        )


def test_parse_response_json_accepts_prose_wrapped_object() -> None:
    parsed = llm_scorer._parse_response_json(
        'Vastaus alla: {"score": 4, "rationale": "ok", "themes": ["teema"]} kiitos.'
    )

    assert parsed["score"] == 4


def test_parse_response_json_rejects_non_object_payload() -> None:
    with pytest.raises(ValueError, match="not valid JSON object"):
        llm_scorer._parse_response_json("[1, 2, 3]")


def test_parse_response_json_ignores_empty_fenced_block() -> None:
    parsed = llm_scorer._parse_response_json(
        '```json\n\n```\n{"score": 3, "rationale": "ok", "themes": []}'
    )

    assert parsed["score"] == 3
