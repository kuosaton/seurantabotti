from __future__ import annotations

import json
from types import SimpleNamespace

import config
import main
from clients.eduskunta import Document, Matter


def _setup(tmp_path, monkeypatch) -> tuple:
    state_dir = tmp_path / "state"
    context_dir = tmp_path / "context"
    state_dir.mkdir()
    context_dir.mkdir()

    seen_docs_path = state_dir / "seen_documents.json"
    score_log_path = state_dir / "score_log.jsonl"
    context_path = context_dir / "kuluttajaliitto.json"

    seen_docs_path.write_text("{}", encoding="utf-8")
    score_log_path.write_text("", encoding="utf-8")
    context_path.write_text(
        json.dumps({"last_updated": None, "recent_statements": [{"title": "x", "excerpt": "y"}]}),
        encoding="utf-8",
    )

    monkeypatch.setattr(config, "SEEN_DOCUMENTS_PATH", seen_docs_path)
    monkeypatch.setattr(config, "SCORE_LOG_PATH", score_log_path)
    monkeypatch.setattr(config, "CONTEXT_PATH", context_path)
    monkeypatch.setattr(config, "NOTIFY_THRESHOLD", 7)
    monkeypatch.setattr(config, "LOG_THRESHOLD", 4)

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

    monkeypatch.setattr(main.httpx, "Client", FakeClient)

    return seen_docs_path, score_log_path, context_path


def _doc(edktunnus="EDK-1", eduskuntatunnus="TaVE 40/2026 vp", tyyppikoodi="TaVE") -> Document:
    return Document(
        edktunnus=edktunnus,
        eduskuntatunnus=eduskuntatunnus,
        tyyppikoodi=tyyppikoodi,
        nimeke="Tiistai 28.4.2026 klo 12.00",
        laadintapvm="2026-04-28",
        julkaistu="2026-04-25T08:00:00.000+00:00",
    )


def _matter(eduskuntatunnus="HE 1/2026 vp", title="Esimerkkimatter") -> Matter:
    return Matter(eduskuntatunnus=eduskuntatunnus, title=title, type="Hallituksen esitys")


def test_cmd_weekly_no_new_agendas_exits_cleanly(tmp_path, monkeypatch, capsys) -> None:
    _setup(tmp_path, monkeypatch)
    monkeypatch.setattr(main, "fetch_committee_page", lambda client, url: "<html/>")
    monkeypatch.setattr(main, "extract_documents", lambda html: [])

    def _should_not_run(*args, **kwargs):
        raise AssertionError("scorer should not run when there are no agendas")

    monkeypatch.setattr(main, "score_item", _should_not_run)

    main.cmd_weekly(dry_run=True)
    out = capsys.readouterr().out
    assert "No new committee agendas" in out


def test_cmd_weekly_skips_already_seen_agendas(tmp_path, monkeypatch, capsys) -> None:
    seen_path, _score_log, _ctx = _setup(tmp_path, monkeypatch)
    seen_path.write_text(
        json.dumps({"EDK-already-seen": {"first_seen": "2026-04-20T00:00:00+00:00"}}),
        encoding="utf-8",
    )

    monkeypatch.setattr(main, "fetch_committee_page", lambda client, url: "<html/>")
    monkeypatch.setattr(
        main,
        "extract_documents",
        lambda html: [_doc(edktunnus="EDK-already-seen")],
    )

    def _should_not_run(*args, **kwargs):
        raise AssertionError("scorer should not run when agenda already seen")

    monkeypatch.setattr(main, "score_item", _should_not_run)

    main.cmd_weekly(dry_run=True)
    out = capsys.readouterr().out
    assert "No new committee agendas" in out


def test_cmd_weekly_aborts_on_user_no(tmp_path, monkeypatch, capsys) -> None:
    seen_path, score_log_path, _ctx = _setup(tmp_path, monkeypatch)

    monkeypatch.setattr(main, "fetch_committee_page", lambda client, url: "<html/>")
    monkeypatch.setattr(main, "extract_documents", lambda html: [_doc()])
    monkeypatch.setattr(main, "fetch_agenda_xml", lambda client, tunnus: "<xml/>")
    monkeypatch.setattr(main, "parse_agenda_matters", lambda xml: [_matter()])
    monkeypatch.setattr("builtins.input", lambda _: "n")

    def _should_not_score(*args, **kwargs):
        raise AssertionError("score_item should not run after abort")

    monkeypatch.setattr(main, "score_item", _should_not_score)

    main.cmd_weekly(dry_run=True)
    out = capsys.readouterr().out
    assert "Aborted." in out
    assert json.loads(seen_path.read_text(encoding="utf-8")) == {}
    assert score_log_path.read_text(encoding="utf-8") == ""


def test_cmd_weekly_dry_run_scores_and_renders_digest(tmp_path, monkeypatch, capsys) -> None:
    seen_path, score_log_path, _ctx = _setup(tmp_path, monkeypatch)

    monkeypatch.setattr(main, "fetch_committee_page", lambda client, url: "<html/>")
    monkeypatch.setattr(main, "extract_documents", lambda html: [_doc()])
    monkeypatch.setattr(main, "fetch_agenda_xml", lambda client, tunnus: "<xml/>")
    monkeypatch.setattr(
        main,
        "parse_agenda_matters",
        lambda xml: [
            _matter(eduskuntatunnus="HE 1/2026 vp", title="Nostettava"),
            _matter(eduskuntatunnus="HE 2/2026 vp", title="Rajatapaus"),
            _matter(eduskuntatunnus="HE 3/2026 vp", title="Pudotettava"),
        ],
    )
    monkeypatch.setattr("builtins.input", lambda _: "y")

    scores_by_title = {"Nostettava": 8, "Rajatapaus": 5, "Pudotettava": 1}
    monkeypatch.setattr(
        main,
        "score_item",
        lambda title, abstract, src, ctx: {
            "score": scores_by_title[title],
            "rationale": f"R-{title}",
            "themes": [],
        },
    )
    monkeypatch.setattr(
        main,
        "build_weekly_digest",
        lambda items, week, total_scored, total_logged: (
            f"SUBJ vko{week}",
            "<html/>",
            f"TEXT scored={total_scored} logged={total_logged} flagged={sum(len(v) for v in items.values())}",
        ),
    )

    def _should_not_send(*args, **kwargs):
        raise AssertionError("send_email should not run in dry-run")

    monkeypatch.setattr(main, "send_email", _should_not_send)

    main.cmd_weekly(dry_run=True)
    out = capsys.readouterr().out

    assert "[FLAG 8/10] HE 1/2026 vp: Nostettava" in out
    assert "[LOG 5/10] HE 2/2026 vp: Rajatapaus" in out
    assert "[DROP 1/10] HE 3/2026 vp: Pudotettava" in out
    assert "DRY RUN" in out
    assert "TEXT scored=3 logged=1 flagged=1" in out

    seen_docs = json.loads(seen_path.read_text(encoding="utf-8"))
    assert "EDK-1" in seen_docs
    matter_scores = seen_docs["EDK-1"]["matter_scores"]
    assert matter_scores["HE 1/2026 vp"]["score"] == 8
    assert matter_scores["HE 1/2026 vp"]["notified"] is False  # dry-run never sets notified

    log_lines = [
        json.loads(line)
        for line in score_log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert {entry["id"] for entry in log_lines} == {
        "HE 1/2026 vp",
        "HE 2/2026 vp",
        "HE 3/2026 vp",
    }
    assert all(entry["source"] == "talousvaliokunta" for entry in log_lines)


def test_cmd_weekly_non_dry_run_sends_email(tmp_path, monkeypatch) -> None:
    _setup(tmp_path, monkeypatch)
    monkeypatch.setattr(main, "fetch_committee_page", lambda client, url: "<html/>")
    monkeypatch.setattr(main, "extract_documents", lambda html: [_doc()])
    monkeypatch.setattr(main, "fetch_agenda_xml", lambda client, tunnus: "<xml/>")
    monkeypatch.setattr(main, "parse_agenda_matters", lambda xml: [_matter()])
    monkeypatch.setattr("builtins.input", lambda _: "y")
    monkeypatch.setattr(
        main,
        "score_item",
        lambda *a, **kw: {"score": 9, "rationale": "OK", "themes": []},
    )
    monkeypatch.setattr(
        main,
        "build_weekly_digest",
        lambda *a, **kw: ("S", "<h/>", "T"),
    )

    captured: dict = {}
    monkeypatch.setattr(
        main,
        "send_email",
        lambda subject, html_body, text_body: captured.update(
            {"subject": subject, "html": html_body, "text": text_body}
        ),
    )

    main.cmd_weekly(dry_run=False)
    assert captured == {"subject": "S", "html": "<h/>", "text": "T"}


def test_cmd_weekly_handles_committee_fetch_error(tmp_path, monkeypatch, capsys) -> None:
    _setup(tmp_path, monkeypatch)

    def _raise(client, url):
        raise RuntimeError("network down")

    monkeypatch.setattr(main, "fetch_committee_page", _raise)

    main.cmd_weekly(dry_run=True)
    out = capsys.readouterr().out
    err = capsys.readouterr().err
    assert "No new committee agendas" in out or "ERROR" in err


def test_cmd_weekly_handles_agenda_fetch_error(tmp_path, monkeypatch, capsys) -> None:
    _setup(tmp_path, monkeypatch)
    monkeypatch.setattr(main, "fetch_committee_page", lambda client, url: "<html/>")
    monkeypatch.setattr(main, "extract_documents", lambda html: [_doc()])

    def _raise(client, tunnus):
        raise RuntimeError("vaski down")

    monkeypatch.setattr(main, "fetch_agenda_xml", _raise)

    main.cmd_weekly(dry_run=True)
    out = capsys.readouterr().out
    assert "No matters scheduled" in out


def test_cmd_weekly_skips_pp_pohjakirja_and_null_tunnus_docs(tmp_path, monkeypatch, capsys) -> None:
    """Only TaVE/MmVE/YmVE (esityslistat) with a non-null eduskuntatunnus should be processed."""
    _setup(tmp_path, monkeypatch)
    docs = [
        _doc(edktunnus="EDK-pp", eduskuntatunnus="TaVP 1/2026 vp", tyyppikoodi="TaVP"),
        SimpleNamespace(
            edktunnus="EDK-vs",
            eduskuntatunnus=None,
            tyyppikoodi="VS",
            nimeke="Viikkosuunnitelma",
            laadintapvm="2026-04-25",
            julkaistu="2026-04-25T08:00:00+00:00",
        ),
    ]
    monkeypatch.setattr(main, "fetch_committee_page", lambda client, url: "<html/>")
    monkeypatch.setattr(main, "extract_documents", lambda html: docs)

    main.cmd_weekly(dry_run=True)
    out = capsys.readouterr().out
    assert "No new committee agendas" in out
