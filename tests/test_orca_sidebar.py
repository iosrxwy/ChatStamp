#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import chat_stamp as ct
import hook as hk


def test_grok_set_title_pins_manual(home: Path):
    sid = "01a0test-grok-title"
    sess = home / ".grok" / "sessions" / "cwd" / sid
    sess.mkdir(parents=True)
    (sess / "summary.json").write_text(
        json.dumps({"generated_title": "修复闪退", "session_summary": "old"}, ensure_ascii=False)
        + "\n"
    )
    assert ct.grok_set_title(sid, "0905｜修复｜闪退")
    data = json.loads((sess / "summary.json").read_text())
    assert data["generated_title"] == "0905｜修复｜闪退"
    assert data["session_summary"] == "0905｜修复｜闪退"
    assert data["title_is_manual"] is True


def test_detect_host_grok_is_orca():
    with patch.dict(os.environ, {"GROK_SESSION_ID": "abc", "GROK_AGENT": "1"}, clear=False):
        assert ct.detect_host() == "orca"


def test_orca_apply_renames_live_tab(home: Path):
    sid = "01a0test-grok-title"
    sess = home / ".grok" / "sessions" / "cwd" / sid
    sess.mkdir(parents=True, exist_ok=True)
    (sess / "summary.json").write_text(
        json.dumps({"generated_title": "朋友圈评论长按复读与选段 clicfg"}, ensure_ascii=False)
        + "\n"
    )
    calls = []

    def fake_run(argv, **kwargs):
        calls.append(list(argv))
        class R:
            returncode = 0
            stdout = "{}"
            stderr = ""
        if "list" in argv:
            R.stdout = json.dumps({"ok": True, "result": {"terminals": []}})
        elif "rename" in argv:
            R.stdout = json.dumps({"ok": True, "result": {"rename": {"title": argv[-1]}}})
        return R()

    with patch.object(ct, "orca_bin", lambda: "/usr/local/bin/orca"):
        with patch.object(ct.subprocess, "run", fake_run):
            with patch.dict(os.environ, {"GROK_SESSION_ID": sid, "ORCA_TERMINAL_HANDLE": "term_abc"}):
                n = ct.orca_apply(
                    [{"id": sid, "title": "0905｜探索｜朋友圈评论复读选段", "engine": "grok"}]
                )
    assert n == 1
    data = json.loads((sess / "summary.json").read_text())
    assert data["title_is_manual"] is True
    assert data["generated_title"] == "0905｜探索｜朋友圈评论复读选段"
    rename = [c for c in calls if "rename" in c]
    assert rename, calls
    assert "term_abc" in rename[0]
    assert "0905｜探索｜朋友圈评论复读选段" in rename[0]


def test_hook_in_grok_never_asks_claude():
    class FakeCT:
        @staticmethod
        def silent_stamp_grok(sid):
            assert sid == "01a070e2"
            return "0905｜功能｜密友长按面容解锁"

        @staticmethod
        def load_config():
            return {"locale": "zh"}

        @staticmethod
        def locale_of(cfg):
            return "zh"

    with patch.dict(os.environ, {"GROK_SESSION_ID": "01a070e2", "GROK_AGENT": "1"}):
        with patch.object(hk, "load_ct", lambda: FakeCT()):
            out = hk.handle("claude", {"session_id": "should-be-ignored"})
    assert out == {}
    text = json.dumps(out)
    assert "claude" not in text.lower()
    assert "chat-stamp-overrides" not in text


def test_hook_grok_followup_uses_host_orca(tmp_path: Path):
    class FakeCT:
        @staticmethod
        def silent_stamp_grok(sid):
            return None

        @staticmethod
        def load_config():
            return {"locale": "zh"}

        @staticmethod
        def locale_of(cfg):
            return "zh"

    once = tmp_path / "once"
    with patch.object(hk, "ONCE", once):
        with patch.dict(os.environ, {"GROK_SESSION_ID": "01a0need-followup", "GROK_AGENT": "1"}):
            with patch.object(hk, "load_ct", lambda: FakeCT()):
                out = hk.handle("claude", {})
    assert out.get("decision") == "block"
    assert "--host orca" in (out.get("reason") or "")
    assert "--host claude" not in (out.get("reason") or "")


def test_followup_text_orca_zh():
    text = hk.followup_text("zh", "orca")
    assert "--host orca" in text
    assert "--host claude" not in text


if __name__ == "__main__":
    import tempfile
    from unittest.mock import patch as _patch

    home = Path(tempfile.mkdtemp())
    with _patch.object(ct, "HOME", home):
        test_grok_set_title_pins_manual(home)
        test_orca_apply_renames_live_tab(home)
    test_detect_host_grok_is_orca()
    test_hook_in_grok_never_asks_claude()
    test_hook_grok_followup_uses_host_orca(Path(tempfile.mkdtemp()))
    test_followup_text_orca_zh()
    print("ok")
