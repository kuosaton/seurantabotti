from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def auto_confirm(monkeypatch):
    def _input(prompt):
        return "0" if prompt.strip() == ">" else "y"

    monkeypatch.setattr("builtins.input", _input)
