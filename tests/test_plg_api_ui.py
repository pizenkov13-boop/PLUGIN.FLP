"""Smoke tests for plg_api helpers added for full UI."""

from __future__ import annotations

import json
from pathlib import Path

import plg_api


def test_get_app_info_has_version_and_docs(tmp_path, monkeypatch):
    monkeypatch.setattr(plg_api, "PROJECT_DIR", tmp_path)
    (tmp_path / "START_HERE.md").write_text("# start", encoding="utf-8")

    info = plg_api.get_app_info()

    assert info["ok"] is True
    assert info["version"] == plg_api.APP_VERSION
    assert "start_here" in info["docs"]
    assert "quota" in info


def test_open_document_opens_file(tmp_path, monkeypatch):
    monkeypatch.setattr(plg_api, "PROJECT_DIR", tmp_path)
    doc = tmp_path / "FL_BRIDGE.md"
    doc.write_text("# bridge", encoding="utf-8")

    called: list[str] = []

    def fake_open(path: str):
        called.append(path)
        return {"ok": True}

    monkeypatch.setattr(plg_api, "open_path", fake_open)
    result = plg_api.open_document("fl_bridge")

    assert result["ok"] is True
    assert called == [str(doc)]


def test_import_kit_folder_copies_and_scans(tmp_path, monkeypatch):
    src = tmp_path / "kit"
    src.mkdir()
    (src / "kick_hard.wav").write_bytes(b"wav")
    out = tmp_path / "library"
    out.mkdir()

    monkeypatch.setattr(plg_api, "CATALOG_FILE", tmp_path / "catalog.json")
    monkeypatch.setattr(plg_api, "get_samples_dir", lambda: str(out))

    result = plg_api.import_kit_folder(str(src))

    assert result["ok"] is True
    assert result["imported"] >= 1
    assert (tmp_path / "catalog.json").is_file()
    catalog = json.loads((tmp_path / "catalog.json").read_text(encoding="utf-8"))
    assert catalog["audio_total"] >= 1


def test_import_kit_folder_missing_dir():
    result = plg_api.import_kit_folder(str(Path("/nonexistent/kit_folder_xyz")))
    assert result["ok"] is False
    assert result["error_type"] == "not_found"
