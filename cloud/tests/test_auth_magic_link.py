from unittest.mock import MagicMock

import shared.config as app_settings
from shared.auth import (
    magic_link_token_may_appear_in_json,
    may_request_magic_link,
    normalize_email,
)


def test_normalize_email():
    assert normalize_email("  Op@Example.COM \n") == "op@example.com"


def test_magic_link_token_hidden_in_production(monkeypatch):
    monkeypatch.setattr(app_settings.settings, "environment", "production")
    assert magic_link_token_may_appear_in_json() is False


def test_magic_link_token_shown_outside_production(monkeypatch):
    monkeypatch.setattr(app_settings.settings, "environment", "development")
    assert magic_link_token_may_appear_in_json() is True


def test_may_request_magic_link_existing_user():
    conn = MagicMock()

    def exec_side(sql: str, params=None):
        r = MagicMock()
        if "SELECT 1 FROM users" in sql:
            r.fetchone.return_value = (1,)
        return r

    conn.execute.side_effect = exec_side
    ok, email = may_request_magic_link(conn, "User@Co.com")
    assert ok is True
    assert email == "user@co.com"
