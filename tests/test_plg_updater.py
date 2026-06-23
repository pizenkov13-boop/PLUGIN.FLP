"""Tests for desktop auto-update helpers."""

from __future__ import annotations

from plg_updater import _parse_version


def test_parse_version_order():
    assert _parse_version("1.0.0") < _parse_version("1.0.1")
    assert _parse_version("1.2.0") < _parse_version("2.0.0")


def test_parse_version_invalid():
    assert _parse_version("beta") == (0, 0, 0)
