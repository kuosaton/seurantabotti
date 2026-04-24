from __future__ import annotations

from types import SimpleNamespace

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


def test_score_item_includes_jakelu_signal(monkeypatch) -> None:
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

    assert "Lisa" in item_text or "Lisäsignaali" in item_text
    assert "Kuluttajaliitto ry" in item_text
    assert result["score"] == 6
