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


def test_main_without_flags_launches_interactive(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["main.py"])
    # Should not raise; interactive mode auto-exits via fixture returning "0"
    main.main()


def test_interactive_menu_choice_daily(monkeypatch) -> None:
    called = {"daily": False}

    def mock_daily(dry_run):
        called["daily"] = True

    # Simulate choosing "1" (daily check) then "0" (exit)
    inputs = ["1", "0"]
    input_iter = iter(inputs)

    def mock_input(prompt):
        val = next(input_iter)
        if prompt.strip() == ">":
            return val
        return "y"

    monkeypatch.setattr("builtins.input", mock_input)
    monkeypatch.setattr(main, "cmd_daily", mock_daily)
    monkeypatch.setattr("sys.argv", ["main.py"])

    main.main()
    assert called["daily"] is True


def test_interactive_menu_choice_daily_dry_run(monkeypatch) -> None:
    called = {"daily_dry_run": False}

    def mock_daily(dry_run):
        if dry_run:
            called["daily_dry_run"] = True

    # Simulate choosing "2" (daily dry run) then "0" (exit)
    inputs = ["2", "0"]
    input_iter = iter(inputs)

    def mock_input(prompt):
        val = next(input_iter)
        if prompt.strip() == ">":
            return val
        return "y"

    monkeypatch.setattr("builtins.input", mock_input)
    monkeypatch.setattr(main, "cmd_daily", mock_daily)
    monkeypatch.setattr("sys.argv", ["main.py"])

    main.main()
    assert called["daily_dry_run"] is True


def test_interactive_menu_choice_update_context(monkeypatch) -> None:
    called = {"update_context": False}

    def mock_update():
        called["update_context"] = True

    # Simulate choosing "3" (update context) then "0" (exit)
    inputs = ["3", "0"]
    input_iter = iter(inputs)

    def mock_input(prompt):
        val = next(input_iter)
        if prompt.strip() == ">":
            return val
        return "y"

    monkeypatch.setattr("builtins.input", mock_input)
    monkeypatch.setattr(main, "cmd_update_context", mock_update)
    monkeypatch.setattr("sys.argv", ["main.py"])

    main.main()
    assert called["update_context"] is True


def test_interactive_menu_choice_review_logged(monkeypatch) -> None:
    called = {"review_logged": False}

    def mock_review(days):
        called["review_logged"] = True

    # Simulate choosing "4" (review 7 days) then "0" (exit)
    inputs = ["4", "0"]
    input_iter = iter(inputs)

    def mock_input(prompt):
        val = next(input_iter)
        if prompt.strip() == ">":
            return val
        return "y"

    monkeypatch.setattr("builtins.input", mock_input)
    monkeypatch.setattr(main, "cmd_review_logged", mock_review)
    monkeypatch.setattr("sys.argv", ["main.py"])

    main.main()
    assert called["review_logged"] is True


def test_interactive_menu_choice_preview_nostetut(monkeypatch) -> None:
    called = {"preview": False}

    def mock_preview():
        called["preview"] = True

    # Simulate choosing "6" (preview nostetut) then "0" (exit)
    inputs = ["6", "0"]
    input_iter = iter(inputs)

    def mock_input(prompt):
        val = next(input_iter)
        if prompt.strip() == ">":
            return val
        return "y"

    monkeypatch.setattr("builtins.input", mock_input)
    monkeypatch.setattr(main, "cmd_preview_nostetut", mock_preview)
    monkeypatch.setattr("sys.argv", ["main.py"])

    main.main()
    assert called["preview"] is True


def test_interactive_menu_choice_reset_state(monkeypatch) -> None:
    called = {"reset": False}

    def mock_reset():
        called["reset"] = True

    # Simulate choosing "7" (reset state) then "0" (exit)
    inputs = ["7", "0"]
    input_iter = iter(inputs)

    def mock_input(prompt):
        val = next(input_iter)
        if prompt.strip() == ">":
            return val
        return "y"

    monkeypatch.setattr("builtins.input", mock_input)
    monkeypatch.setattr(main, "cmd_reset_state", mock_reset)
    monkeypatch.setattr("sys.argv", ["main.py"])

    main.main()
    assert called["reset"] is True


def test_interactive_menu_invalid_choice(monkeypatch) -> None:
    # Simulate choosing an invalid option, then "0" (exit)
    inputs = ["99", "0"]
    input_iter = iter(inputs)

    def mock_input(prompt):
        val = next(input_iter)
        if prompt.strip() == ">":
            return val
        return "y"

    monkeypatch.setattr("builtins.input", mock_input)
    monkeypatch.setattr("sys.argv", ["main.py"])

    # Should not raise, just print error and continue
    main.main()


def test_interactive_menu_choice_review_custom_days_valid(monkeypatch) -> None:
    called = {"days": None}
    inputs = ["5", "14", "0"]
    input_iter = iter(inputs)

    def mock_input(prompt):
        if prompt.strip() == ">":
            return next(input_iter)
        if "Days to look back" in prompt:
            return next(input_iter)
        return "y"

    monkeypatch.setattr("builtins.input", mock_input)
    monkeypatch.setattr(main, "cmd_review_logged", lambda days: called.__setitem__("days", days))
    monkeypatch.setattr("sys.argv", ["main.py"])

    main.main()
    assert called["days"] == 14


def test_interactive_menu_choice_review_custom_days_invalid(monkeypatch, capsys) -> None:
    called = {"count": 0}
    inputs = ["5", "oops", "0"]
    input_iter = iter(inputs)

    def mock_input(prompt):
        if prompt.strip() == ">":
            return next(input_iter)
        if "Days to look back" in prompt:
            return next(input_iter)
        return "y"

    monkeypatch.setattr("builtins.input", mock_input)
    monkeypatch.setattr(
        main,
        "cmd_review_logged",
        lambda days: called.__setitem__("count", called["count"] + 1),
    )
    monkeypatch.setattr("sys.argv", ["main.py"])

    main.main()
    out = capsys.readouterr().out
    assert "Invalid number" in out
    assert called["count"] == 0


def test_cmd_interactive_handles_keyboard_interrupt(monkeypatch) -> None:
    def _raise_interrupt(prompt):
        raise KeyboardInterrupt

    monkeypatch.setattr("builtins.input", _raise_interrupt)
    main.cmd_interactive()


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


def test_main_dispatches_reset_state_flag(monkeypatch) -> None:
    called = {"reset": False}

    monkeypatch.setattr(main, "cmd_update_context", lambda: None)
    monkeypatch.setattr(main, "cmd_daily", lambda dry_run: None)
    monkeypatch.setattr(main, "cmd_weekly", lambda dry_run: None)
    monkeypatch.setattr(main, "cmd_midweek", lambda dry_run: None)
    monkeypatch.setattr(main, "cmd_review_logged", lambda days: None)
    monkeypatch.setattr(main, "cmd_preview_nostetut", lambda: None)
    monkeypatch.setattr(main, "cmd_reset_state", lambda: called.__setitem__("reset", True))
    monkeypatch.setattr("sys.argv", ["main.py", "--reset-state"])

    main.main()
    assert called["reset"] is True


def test_main_dispatches_interactive_flag(monkeypatch) -> None:
    called = {"interactive": False}

    monkeypatch.setattr(main, "cmd_update_context", lambda: None)
    monkeypatch.setattr(main, "cmd_daily", lambda dry_run: None)
    monkeypatch.setattr(main, "cmd_weekly", lambda dry_run: None)
    monkeypatch.setattr(main, "cmd_midweek", lambda dry_run: None)
    monkeypatch.setattr(main, "cmd_review_logged", lambda days: None)
    monkeypatch.setattr(main, "cmd_preview_nostetut", lambda: None)
    monkeypatch.setattr(main, "cmd_reset_state", lambda: None)
    monkeypatch.setattr(
        main,
        "cmd_interactive",
        lambda: called.__setitem__("interactive", True),
    )
    monkeypatch.setattr("sys.argv", ["main.py", "--interactive"])

    main.main()
    assert called["interactive"] is True
