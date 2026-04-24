from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def auto_confirm(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "y")
