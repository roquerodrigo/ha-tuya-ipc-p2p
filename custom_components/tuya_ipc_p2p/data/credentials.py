"""Typed shape of the credentials a config flow step collects."""

from __future__ import annotations

from typing import TypedDict


class TuyaIpcP2pCredentials(TypedDict):
    """What the user types into the account form."""

    email: str
    password: str
    country_code: str
    region: str
