"""Import PLG MIDI into FL Studio (menu automation + fallbacks)."""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wintypes
import logging
import subprocess
import time
from pathlib import Path

user32 = ctypes.windll.user32
shell32 = ctypes.windll.shell32

WM_SETTEXT = 0x000C
WM_COMMAND = 0x0111
IDOK = 1
KEYEVENTF_KEYUP = 0x0002
VK_MENU = 0x12
VK_RETURN = 0x0D
VK_TAB = 0x09
VK_SPACE = 0x20

FL_WINDOW_HINTS = ("FL Studio",)
OPEN_DIALOG_TITLES = ("open", "открыть", "import", "импорт", "midi")
IMPORT_DIALOG_TITLES = ("import midi", "импорт midi", "midi data", "midi data import")


def import_marker_path(project_dir: Path) -> Path:
    return project_dir / ".plg_fl_import_ready"


def is_fl_import_configured(project_dir: Path) -> bool:
    return import_marker_path(project_dir).is_file()


def mark_fl_import_configured(project_dir: Path) -> None:
    import_marker_path(project_dir).write_text("ok\n", encoding="utf-8")


def find_fl_window() -> int | None:
    matches: list[int] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd: int, _lparam: int) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value
        if any(hint in title for hint in FL_WINDOW_HINTS):
            matches.append(hwnd)
        return True

    user32.EnumWindows(callback, 0)
    return matches[0] if matches else None


def wait_for_fl_window(timeout: float = 60.0, poll: float = 0.5) -> int | None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        hwnd = find_fl_window()
        if hwnd is not None:
            time.sleep(2.5)
            return hwnd
        time.sleep(poll)
    return None


def _focus_window(hwnd: int) -> None:
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, 9)
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.35)


def _tap_vk(vk: int, *, alt: bool = False) -> None:
    if alt:
        user32.keybd_event(VK_MENU, 0, 0, 0)
    user32.keybd_event(vk, 0, 0, 0)
    user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
    if alt:
        user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.12)


def _tap_char(ch: str, *, alt: bool = False) -> None:
    code = user32.VkKeyScanW(ord(ch))
    if code == -1:
        return
    vk = code & 0xFF
    _tap_vk(vk, alt=alt)


def _enum_windows_matching(
    *,
    class_name: str | None = None,
    title_predicate: str | None = None,
) -> list[int]:
    found: list[int] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd: int, _lparam: int) -> bool:
        if class_name:
            buf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, buf, 256)
            if buf.value != class_name:
                return True
        length = user32.GetWindowTextLengthW(hwnd)
        title = ""
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value
        if title_predicate and title_predicate not in title.lower():
            return True
        if user32.IsWindowVisible(hwnd):
            found.append(hwnd)
        return True

    user32.EnumWindows(callback, 0)
    return found


def _wait_for_dialog(
    title_keywords: tuple[str, ...],
    *,
    timeout: float = 10.0,
    class_name: str | None = "#32770",
) -> int | None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        for hwnd in _enum_windows_matching(class_name=class_name):
            length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                continue
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value.lower()
            if any(key in title for key in title_keywords):
                return hwnd
        time.sleep(0.2)
    return None


def _find_dialog_edit(hwnd: int) -> int | None:
    for child_id in (1148, 1152, 1001, 1002):
        edit = user32.GetDlgItem(hwnd, child_id)
        if edit:
            return edit

    edits: list[int] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def callback(child: int, _lparam: int) -> bool:
        buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(child, buf, 256)
        if buf.value == "Edit":
            edits.append(child)
        return True

    user32.EnumChildWindows(hwnd, callback, 0)
    return edits[0] if edits else None


def _fill_open_dialog(hwnd: int, file_path: str) -> bool:
    edit = _find_dialog_edit(hwnd)
    if not edit:
        return False
    user32.SendMessageW(edit, WM_SETTEXT, 0, file_path)
    time.sleep(0.1)
    user32.SendMessageW(hwnd, WM_COMMAND, IDOK, 0)
    return True


def _trigger_file_import_midi(fl_hwnd: int) -> None:
    _focus_window(fl_hwnd)
    # English FL: File -> Import -> MIDI file
    _tap_char("f", alt=True)
    time.sleep(0.45)
    _tap_char("i")
    time.sleep(0.25)
    _tap_char("m")
    time.sleep(0.35)
    # Russian FL fallback
    if _wait_for_dialog(OPEN_DIALOG_TITLES, timeout=1.2):
        return
    _focus_window(fl_hwnd)
    _tap_char("f", alt=True)
    time.sleep(0.45)
    for _ in range(4):
        _tap_vk(0x28)  # VK_DOWN
    _tap_vk(VK_RETURN)
    time.sleep(0.25)
    _tap_vk(VK_RETURN)


def _confirm_import_options(*, configured: bool) -> None:
    time.sleep(0.8)
    dialog = _wait_for_dialog(IMPORT_DIALOG_TITLES, timeout=8.0, class_name="#32770")
    if dialog is None:
        dialog = _wait_for_dialog(IMPORT_DIALOG_TITLES, timeout=3.0, class_name=None)
    if dialog is None:
        logging.warning("FL MIDI import options dialog not found — sending Enter")
        _tap_vk(VK_RETURN)
        return

    _focus_window(dialog)
    if not configured:
        # Tab to "Create one channel per track", toggle, accept
        for _ in range(5):
            _tap_vk(VK_TAB)
        _tap_vk(VK_SPACE)
        time.sleep(0.1)
    _tap_vk(VK_RETURN)


def reveal_midi_in_explorer(midi_path: Path) -> None:
    path = str(midi_path.resolve())
    subprocess.Popen(["explorer", "/select,", path], close_fds=True)


def import_midi_into_fl(fl_hwnd: int, midi_path: Path, *, configured: bool) -> bool:
    if not midi_path.is_file():
        return False

    logging.info("FL import: menu automation for %s", midi_path.name)
    _trigger_file_import_midi(fl_hwnd)

    open_dialog = _wait_for_dialog(OPEN_DIALOG_TITLES, timeout=12.0)
    if open_dialog is None:
        logging.warning("FL Open dialog not found")
        return False

    if not _fill_open_dialog(open_dialog, str(midi_path.resolve())):
        logging.warning("FL Open dialog: could not set path")
        return False

    _confirm_import_options(configured=configured)
    return True


def launch_fl_and_import_midi(
    fl_exe: Path,
    midi_path: Path,
    *,
    project_dir: Path,
    wait_timeout: float = 60.0,
) -> dict[str, bool | str]:
    """Start FL if needed, import PLG_Beat.mid into channel rack."""
    hwnd = find_fl_window()
    launched = False
    if hwnd is None:
        subprocess.Popen([str(fl_exe)], cwd=str(fl_exe.parent), close_fds=True)
        launched = True
        hwnd = wait_for_fl_window(timeout=wait_timeout)
    if hwnd is None:
        return {"imported": False, "method": "none", "launched": launched}

    configured = is_fl_import_configured(project_dir)
    ok = import_midi_into_fl(hwnd, midi_path, configured=configured)
    if ok and not configured:
        mark_fl_import_configured(project_dir)

    if not ok:
        reveal_midi_in_explorer(midi_path)

    return {
        "imported": ok,
        "method": "menu" if ok else "explorer_fallback",
        "launched": launched,
        "import_configured": configured or ok,
    }
