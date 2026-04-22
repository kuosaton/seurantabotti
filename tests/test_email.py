from __future__ import annotations

from datetime import datetime
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

    email_mod.send_email(
        subject="Testisubject",
        html_body="<p>Hei</p>",
        text_body="Hei",
        to="vastaanottaja@example.com",
        smtp_host="smtp.example.com",
        smtp_port=2525,
        smtp_user="lahettaja@example.com",
        smtp_pass="salasana",
    )

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
    assert "Asumista koskeva luonnos" in text_body
    assert "Relevanssi: 8/10" in text_body
    assert "https://example.invalid/proposal/1" in text_body
    assert "Teemat: asuminen, kuluttajansuoja" in html_body


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
