from __future__ import annotations

import pytest

import main


def test_main_dispatches_preview(monkeypatch) -> None:
    called = {"preview": False}

    monkeypatch.setattr(main, "cmd_preview_nostetut", lambda: called.__setitem__("preview", True))
    monkeypatch.setattr(main, "cmd_daily", lambda dry_run: None)
    monkeypatch.setattr(main, "cmd_weekly", lambda dry_run: None)
    monkeypatch.setattr(main, "cmd_midweek", lambda dry_run: None)
    monkeypatch.setattr(main, "cmd_update_context", lambda: None)
    monkeypatch.setattr(main, "cmd_review_logged", lambda days: None)
    monkeypatch.setattr(
        "sys.argv",
        ["main.py", "--preview-nostetut"],
    )

    main.main()
    assert called["preview"] is True


def test_main_without_flags_exits(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["main.py"])
    with pytest.raises(SystemExit) as exc:
        main.main()
    assert exc.value.code == 1


def test_unimplemented_commands_exit() -> None:
    with pytest.raises(SystemExit) as weekly:
        main.cmd_weekly(dry_run=True)
    with pytest.raises(SystemExit) as midweek:
        main.cmd_midweek(dry_run=True)
    assert weekly.value.code == 1
    assert midweek.value.code == 1


def test_main_dispatches_all_selected_flags(monkeypatch) -> None:
    called = {
        "update_context": 0,
        "daily": 0,
        "weekly": 0,
        "midweek": 0,
        "review_logged": 0,
        "preview": 0,
    }

    monkeypatch.setattr(main, "cmd_update_context", lambda: called.__setitem__("update_context", 1))
    monkeypatch.setattr(
        main, "cmd_daily", lambda dry_run: called.__setitem__("daily", int(dry_run))
    )
    monkeypatch.setattr(
        main, "cmd_weekly", lambda dry_run: called.__setitem__("weekly", int(dry_run))
    )
    monkeypatch.setattr(
        main, "cmd_midweek", lambda dry_run: called.__setitem__("midweek", int(dry_run))
    )
    monkeypatch.setattr(
        main, "cmd_review_logged", lambda days: called.__setitem__("review_logged", days)
    )
    monkeypatch.setattr(main, "cmd_preview_nostetut", lambda: called.__setitem__("preview", 1))
    monkeypatch.setattr(
        "sys.argv",
        [
            "main.py",
            "--update-context",
            "--daily",
            "--weekly",
            "--midweek",
            "--review-logged",
            "--days",
            "3",
            "--preview-nostetut",
            "--dry-run",
        ],
    )

    main.main()

    assert called["update_context"] == 1
    assert called["daily"] == 1
    assert called["weekly"] == 1
    assert called["midweek"] == 1
    assert called["review_logged"] == 3
    assert called["preview"] == 1
