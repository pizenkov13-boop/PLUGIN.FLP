"""Tests for Phase 5 legal helpers."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from cloud.app.legal import legal_snapshot, require_terms_acceptance


def test_legal_snapshot_has_ownership():
    snap = legal_snapshot()
    assert "beat_ownership" in snap["disclaimers"]
    assert snap["subscription"]["cancel_anytime"] is True


def test_require_terms_blocks():
    with pytest.raises(HTTPException) as exc:
        require_terms_acceptance(False, True)
    assert exc.value.status_code == 400


def test_require_age_blocks():
    with pytest.raises(HTTPException) as exc:
        require_terms_acceptance(True, False)
    assert exc.value.status_code == 400


def test_require_terms_ok():
    require_terms_acceptance(True, True)
