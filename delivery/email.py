from __future__ import annotations

import os
import smtplib
from datetime import date, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import COMMITTEE_DISPLAY_NAMES

_SMTP_HOST = "smtp.gmail.com"
_SMTP_PORT = 587


def _fmt_date(d: date | datetime) -> str:
    return f"{d.day}.{d.month}.{d.year}"


def send_email(subject: str, html_body: str, text_body: str) -> None:
    to = os.environ.get("RECIPIENT_EMAIL", "")
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(_SMTP_HOST, _SMTP_PORT) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)


# ---------------------------------------------------------------------------
# Daily lausuntopalvelu digest
# ---------------------------------------------------------------------------


def build_daily_digest(flagged: list[dict]) -> tuple[str, str, str]:
    today = _fmt_date(date.today())
    count = len(flagged)
    subject = f"Uusia lausuntopyyntöjä, {today}"

    lines = [f"{count} uutta lausuntopyyntöä, jotka saattavat kiinnostaa Kuluttajaliittoa:\n"]
    for item in flagged:
        p = item["proposal"]
        deadline_str = _fmt_date(p.deadline) if p.deadline else "–"
        lines += [
            f"▸ {p.title}",
            f"   Pyytäjä:   {p.organization_name}",
            f"   Määräaika: {deadline_str}",
            f"   Relevanssi: {item['score']}/10",
            f"   {item['rationale']}",
            f"   {p.url}",
            "",
        ]
    text_body = "\n".join(lines)

    item_html = ""
    for item in flagged:
        p = item["proposal"]
        deadline_str = _fmt_date(p.deadline) if p.deadline else "–"
        themes = ", ".join(item.get("themes", []))
        item_html += f"""
        <div style="margin-bottom:24px;padding:16px;border-left:4px solid #1a56a0;background:#f8f9fa;">
          <p style="margin:0 0 6px;font-size:15px;font-weight:bold;">
            <a href="{p.url}" style="color:#1a56a0;text-decoration:none;">{p.title}</a>
          </p>
          <table style="font-size:13px;color:#555;border-collapse:collapse;">
            <tr><td style="padding:2px 12px 2px 0;white-space:nowrap;">Pyytäjä</td><td>{p.organization_name}</td></tr>
            <tr><td style="padding:2px 12px 2px 0;white-space:nowrap;">Määräaika</td><td>{deadline_str}</td></tr>
            <tr><td style="padding:2px 12px 2px 0;white-space:nowrap;">Relevanssi</td><td>{item["score"]}/10</td></tr>
          </table>
          <p style="margin:8px 0 0;font-size:13px;color:#333;">{item["rationale"]}</p>
          {f'<p style="margin:4px 0 0;font-size:12px;color:#888;">Teemat: {themes}</p>' if themes else ""}
        </div>"""

    html_body = f"""<!DOCTYPE html>
<html lang="fi">
<head><meta charset="utf-8"><title>{subject}</title></head>
<body style="font-family:Arial,sans-serif;max-width:680px;margin:0 auto;padding:24px;color:#222;">
  <h2 style="color:#1a56a0;margin-bottom:4px;">Uusia lausuntopyyntöjä</h2>
  <p style="color:#666;margin-top:0;">{today} &mdash; {count} uutta ehdotusta</p>
  {item_html}
  <hr style="border:none;border-top:1px solid #ddd;margin:32px 0 16px;">
  <p style="font-size:11px;color:#aaa;">Seurantabotti</p>
</body>
</html>"""

    return subject, html_body, text_body


# ---------------------------------------------------------------------------
# Weekly committee digest
# ---------------------------------------------------------------------------


def _weekly_text_body(
    committee_items: dict[str, list[dict]],
    week_number: int,
    total_flagged: int,
    total_scored: int,
    total_logged: int,
) -> str:
    lines = [f"Viikkokatsaus, vko {week_number}\n"]
    for key, items in committee_items.items():
        name = COMMITTEE_DISPLAY_NAMES.get(key, key)
        lines.append(f"--- {name.upper()} ---\n")
        if not items:
            lines.append("Ei nostettavia asioita.\n")
        for item in items:
            lines += [
                f"▸ {item['title']}",
                f"   Tunnus:     {item.get('eduskuntatunnus', '–')}",
                f"   Relevanssi: {item['score']}/10",
                f"   {item['rationale']}",
                f"   {item.get('url', '')}",
                "",
            ]
    lines += [
        "---",
        f"Arvioitu yhteensä: {total_scored} asiaa",
        f"Nostettu: {total_flagged}",
        f"Lokitettu (pistemäärä 4–6): {total_logged}",
    ]
    return "\n".join(lines)


def _weekly_html_sections(committee_items: dict[str, list[dict]]) -> str:
    sections_html = ""
    for key, items in committee_items.items():
        name = COMMITTEE_DISPLAY_NAMES.get(key, key)
        items_html = ""
        if not items:
            items_html = '<p style="color:#888;font-size:13px;">Ei nostettavia asioita.</p>'
        for item in items:
            themes = ", ".join(item.get("themes", []))
            items_html += f"""
            <div style="margin-bottom:20px;padding:14px;border-left:4px solid #1a56a0;background:#f8f9fa;">
              <p style="margin:0 0 4px;font-size:14px;font-weight:bold;">
                {f'<a href="{item["url"]}" style="color:#1a56a0;text-decoration:none;">' if item.get("url") else ""}{item["title"]}{("</a>" if item.get("url") else "")}
              </p>
              <p style="margin:0 0 4px;font-size:12px;color:#666;">{item.get("eduskuntatunnus", "")}</p>
              <p style="margin:4px 0;font-size:13px;"><strong>Relevanssi:</strong> {item["score"]}/10</p>
              <p style="margin:4px 0;font-size:13px;color:#333;">{item["rationale"]}</p>
              {f'<p style="margin:4px 0;font-size:12px;color:#888;">Teemat: {themes}</p>' if themes else ""}
            </div>"""
        sections_html += f"""
        <h3 style="color:#1a56a0;border-bottom:1px solid #ddd;padding-bottom:6px;">{name}</h3>
        {items_html}"""
    return sections_html


def build_weekly_digest(
    committee_items: dict[str, list[dict]],
    week_number: int,
    total_scored: int,
    total_logged: int,
) -> tuple[str, str, str]:
    subject = f"Seurantabotti viikkokatsaus, vko {week_number}"
    total_flagged = sum(len(v) for v in committee_items.values())
    text_body = _weekly_text_body(
        committee_items, week_number, total_flagged, total_scored, total_logged
    )
    sections_html = _weekly_html_sections(committee_items)
    html_body = f"""<!DOCTYPE html>
<html lang="fi">
<head><meta charset="utf-8"><title>{subject}</title></head>
<body style="font-family:Arial,sans-serif;max-width:680px;margin:0 auto;padding:24px;color:#222;">
  <h2 style="color:#1a56a0;margin-bottom:4px;">Valiokuntakatsaus</h2>
  <p style="color:#666;margin-top:0;">Viikko {week_number}</p>
  {sections_html}
  <hr style="border:none;border-top:1px solid #ddd;margin:32px 0 16px;">
  <p style="font-size:12px;color:#888;">
    Arvioitu: {total_scored} asiaa &mdash; Nostettu: {total_flagged} &mdash;
    Lokitettu (4–6): {total_logged}
  </p>
  <p style="font-size:11px;color:#aaa;">Seurantabotti</p>
</body>
</html>"""
    return subject, html_body, text_body
