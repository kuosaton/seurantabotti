from __future__ import annotations

from datetime import date, datetime
from types import SimpleNamespace

import delivery.email as email_mod


def test_send_email_uses_smtp_flow(monkeypatch) -> None:
    calls: dict = {}

    class FakeSMTP:
        def __init__(self, host, port):
            calls["host"] = host
            calls["port"] = port

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def starttls(self):
            calls["starttls"] = True

        def login(self, user, password):
            calls["login"] = (user, password)

        def send_message(self, msg):
            calls["subject"] = msg["Subject"]
            calls["to"] = msg["To"]

    monkeypatch.setattr(email_mod.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(email_mod, "_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(email_mod, "_SMTP_PORT", 2525)
    monkeypatch.setenv("RECIPIENT_EMAIL", "vastaanottaja@example.com")
    monkeypatch.setenv("SMTP_USER", "lahettaja@example.com")
    monkeypatch.setenv("SMTP_PASS", "salasana")

    email_mod.send_email(subject="Testisubject", html_body="<p>Hei</p>", text_body="Hei")

    assert calls["host"] == "smtp.example.com"
    assert calls["port"] == 2525
    assert calls["starttls"] is True
    assert calls["login"] == ("lahettaja@example.com", "salasana")
    assert calls["subject"] == "Testisubject"
    assert calls["to"] == "vastaanottaja@example.com"


def test_build_daily_digest_contains_key_fields() -> None:
    flagged = [
        {
            "proposal": SimpleNamespace(
                title="Asumista koskeva luonnos",
                organization_name="Ympäristöministeriö",
                published_on=datetime(2026, 4, 21),
                deadline=datetime(2026, 5, 8),
                url="https://example.invalid/proposal/1",
            ),
            "score": 8,
            "rationale": "Selkeä kuluttajavaikutus.",
            "themes": ["asuminen", "kuluttajansuoja"],
        }
    ]

    subject, html_body, text_body = email_mod.build_daily_digest(flagged)
    assert "Uusia lausuntopyyntöjä" in subject
    assert "pistemäärä 8" in text_body  # score range in header
    assert "[8/10] Asumista koskeva luonnos" in text_body  # score on title line
    assert "Relevanssi" not in text_body  # no longer a separate field
    assert "Julkaistu: 21.4.2026" in text_body
    assert "https://example.invalid/proposal/1" in text_body
    assert "8.5.2026" in text_body
    assert "pv" in text_body
    assert "Teemat:    asuminen, kuluttajansuoja" in text_body
    assert "─" in text_body  # separator present
    assert "Julkaistu" in html_body
    assert "Teemat: asuminen, kuluttajansuoja" in html_body
    assert "pv" in html_body


def test_build_daily_digest_sorts_by_score_descending() -> None:
    def _proposal(title: str) -> SimpleNamespace:
        return SimpleNamespace(
            title=title,
            organization_name="Org",
            published_on=datetime(2026, 4, 1),
            deadline=datetime(2026, 5, 30),
            url="https://example.invalid/p/1",
        )

    flagged = [
        {"proposal": _proposal("Matala"), "score": 6, "rationale": "R", "themes": []},
        {"proposal": _proposal("Korkea"), "score": 9, "rationale": "R", "themes": []},
        {"proposal": _proposal("Keski"), "score": 7, "rationale": "R", "themes": []},
    ]

    _, _, text_body = email_mod.build_daily_digest(flagged)
    pos_korkea = text_body.index("Korkea")
    pos_keski = text_body.index("Keski")
    pos_matala = text_body.index("Matala")
    assert pos_korkea < pos_keski < pos_matala


def test_build_daily_digest_deadline_today() -> None:
    proposal = SimpleNamespace(
        title="T",
        organization_name="Org",
        published_on=datetime(2026, 4, 1),
        deadline=datetime.combine(date.today(), datetime.min.time()),
        url="https://example.invalid/p/1",
    )
    _, _, text_body = email_mod.build_daily_digest(
        [{"proposal": proposal, "score": 7, "rationale": "R", "themes": []}]
    )
    assert "tänään" in text_body


def test_build_daily_digest_omits_url_line_when_empty() -> None:
    proposal = SimpleNamespace(
        title="Ei urlia",
        organization_name="Org",
        published_on=datetime(2026, 4, 1),
        deadline=None,
        url="",
    )
    _, _, text_body = email_mod.build_daily_digest(
        [{"proposal": proposal, "score": 7, "rationale": "R", "themes": []}]
    )
    lines = text_body.splitlines()
    assert not any(line.strip() == "" and line.startswith("   ") for line in lines)


def test_build_weekly_digest_handles_empty_and_linked_items() -> None:
    committee_items = {
        "talousvaliokunta": [
            {
                "eduskuntatunnus": "TaVE 1/2026 vp",
                "title": "HE 1/2026 vp",
                "score": 7,
                "rationale": "Merkittävä kuluttajavaikutus.",
                "themes": ["kuluttajansuoja"],
                "url": "https://example.invalid/doc/1",
            }
        ],
        "ymparistovaliokunta": [],
    }

    subject, html_body, text_body = email_mod.build_weekly_digest(
        committee_items=committee_items,
        week_number=17,
        total_scored=9,
        total_logged=2,
    )

    assert "vko 17" in subject
    assert "TALOUSVALIOKUNTA" in text_body
    assert "Ei nostettavia asioita." in text_body
    assert "Arvioitu yhteensä: 9 asiaa" in text_body
    assert "https://example.invalid/doc/1" in html_body
