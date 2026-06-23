"""Tests for Phase 6 ops helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from cloud.app.feedback import submit_feedback
from cloud.app.status_page import status_payload


def test_status_payload_shape():
    client = MagicMock()
    client.table.return_value.select.return_value.is_.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[]
    )
    with patch("cloud.app.status_page.redis_available", return_value=False):
        with patch("cloud.app.status_page._component_status", return_value="operational"):
            payload = status_payload(client)
    assert payload["ok"] is True
    assert payload["overall"] in ("operational", "degraded", "outage")
    assert "support" in payload
    assert payload["support"]["email"]


def test_submit_feedback_requires_message():
    client = MagicMock()
    with pytest.raises(HTTPException) as exc:
        submit_feedback(client, user_id="u1", email="a@b.c", category="bug", message="  ")
    assert exc.value.status_code == 400


def test_submit_feedback_ok():
    client = MagicMock()
    with patch("cloud.app.feedback.send_email"):
        result = submit_feedback(
            client,
            user_id="u1",
            email="user@test.com",
            category="bug",
            message="App crashed on generate",
        )
    assert result["ok"] is True
    client.table.assert_called_with("feedback_submissions")
