#!/usr/bin/env python3
"""Stop / SessionEnd hook: silent wrap when possible, else one followup."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ONCE = Path.home() / ".config" / "chat-stamp" / "once"


def stdin_json() -> dict:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _id_from_mapping(obj: dict) -> str:
    for key in (
        "conversation_id",
        "conversationId",
        "session_id",
        "sessionId",
        "thread_id",
        "composerId",
        "composer_id",
    ):
        val = obj.get(key)
        if val:
            return str(val)
    return ""


def session_id(event: dict) -> str:
    found = _id_from_mapping(event)
    if found:
        return found
    for nest in ("conversation", "input", "session", "composer", "data"):
        obj = event.get(nest)
        if isinstance(obj, dict):
            found = _id_from_mapping(obj)
            if found:
                return found
    return (
        os.environ.get("GROK_SESSION_ID")
        or os.environ.get("CURSOR_CONVERSATION_ID")
        or os.environ.get("CODEX_THREAD_ID")
        or ""
    )


def running_in_grok() -> bool:
    return bool(os.environ.get("GROK_SESSION_ID") or os.environ.get("GROK_AGENT"))


def load_ct():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import chat_stamp as ct

    return ct


def looks_like_cursor_event(event: dict) -> bool:
    """Cursor stop also runs ~/.claude Stop hooks; skip those so we do not double-fire."""
    has_cursor = bool(event.get("conversation_id") or event.get("conversationId") or event.get("composerId"))
    has_claude = bool(
        event.get("session_id")
        or event.get("sessionId")
        or event.get("hook_event_name")
        or event.get("transcript_path")
    )
    return has_cursor and not has_claude


def followup_text(locale: str, host: str = "cursor", ready_title: str = "") -> str:
    """Cursor expands the leading /tu into the full command rules; keep it short."""
    if host in ("orca", "grok"):
        if ready_title:
            if locale == "en":
                return (
                    f"Apply title {ready_title!r} with "
                    "scripts/chat_stamp.py apply --host orca. Title only."
                )
            return (
                f"把本会话标题写成「{ready_title}」，"
                "用 scripts/chat_stamp.py apply --host orca 写入。只改标题。"
            )
        if locale == "en":
            return (
                "Use the chat-stamp skill for this session only: read my messages and your "
                "wrap-up (strip code), write MMDD | type | topic in English, then apply it "
                "with scripts/chat_stamp.py apply --host orca. Title only."
            )
        return (
            "用 chat-stamp skill 只给本会话起标题：看我发的消息和你的回复总结（去掉代码），"
            "用中文写成 MMDD｜类型｜主题，再用 scripts/chat_stamp.py apply --host orca 写入。只改标题。"
        )
    if ready_title:
        if host == "claude":
            if locale == "en":
                return (
                    f"Apply title {ready_title!r} for this session with "
                    "scripts/chat_stamp.py apply --host claude. Title only."
                )
            return (
                f"把本会话标题写成「{ready_title}」，"
                "用 scripts/chat_stamp.py apply --host claude 写入。只改标题。"
            )
        if locale == "en":
            return f"/tu rename_chat to {ready_title!r} only. Title only."
        return f"/tu 直接 rename_chat 为「{ready_title}」。只改标题。"
    if host == "claude":
        if locale == "en":
            return (
                "Use the chat-stamp skill for this session only: read my messages and your "
                "wrap-up (strip code), write MMDD | type | topic in English, then apply it "
                "with scripts/chat_stamp.py apply --host claude. Title only."
            )
        return (
            "用 chat-stamp skill 只给本会话起标题：看我发的消息和你的回复总结（去掉代码），"
            "用中文写成 MMDD｜类型｜主题，再用 scripts/chat_stamp.py apply --host claude 写入。只改标题。"
        )
    if locale == "en":
        return (
            "/tu Read my messages and your wrap-up (strip code). "
            "Write MMDD | type | topic in English, then rename_chat."
        )
    return "/tu 看我发的消息和你的回复总结（去掉代码），用中文写成 MMDD｜类型｜主题并 rename_chat。"


LOG = Path.home() / ".config" / "chat-stamp" / "hook.log"


def log(msg: str) -> None:
    """One line per stop; file is capped so it never grows unbounded."""
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        if LOG.exists() and LOG.stat().st_size > 200_000:
            LOG.write_text("")
        with LOG.open("a") as fh:
            fh.write(f"{datetime.now().isoformat(timespec='seconds')} {msg}\n")
    except OSError:
        pass


def once_path(host: str, sid: str) -> Path:
    return ONCE / f"{host}-{sid}"


def mark_once(host: str, sid: str) -> bool:
    try:
        ONCE.mkdir(parents=True, exist_ok=True)
        once_path(host, sid).write_text("1\n")
        return True
    except OSError:
        return False


def record_codex(sid: str) -> None:
    try:
        ONCE.mkdir(parents=True, exist_ok=True)
        pending = Path.home() / ".config" / "chat-stamp" / "pending.jsonl"
        with pending.open("a") as fh:
            fh.write(json.dumps({"host": "codex", "id": sid}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def handle_grok(event: dict) -> dict:
    sid = (os.environ.get("GROK_SESSION_ID") or session_id(event) or "").strip()
    if not sid:
        log("grok noop no-id")
        return {}
    if event.get("stop_hook_active"):
        return {}
    try:
        ct = load_ct()
        written = ct.silent_stamp_grok(sid)
        if written:
            log(f"grok {sid} silent {written!r}")
            return {}
        if once_path("orca", sid).exists() or once_path("grok", sid).exists():
            log(f"grok {sid} noop once")
            return {}
        if not mark_once("orca", sid):
            return {}
        locale = ct.locale_of(ct.load_config())
        text = followup_text(locale, "orca")
        log(f"grok {sid} followup")
        return {"decision": "block", "reason": text}
    except Exception as exc:
        log(f"grok {sid} error {exc!r}")
        return {}


def handle(host: str, event: dict) -> dict:
    if running_in_grok():
        return handle_grok(event)
    sid = session_id(event)
    if host == "codex":
        record_codex(sid)
        return {}
    if host == "claude":
        # Cursor stop also executes ~/.claude Stop hooks with the same composer id.
        in_cursor = False
        try:
            in_cursor = bool(sid) and bool(load_ct().cursor_current_title(sid))
        except Exception:
            in_cursor = False
        if looks_like_cursor_event(event) or in_cursor:
            log(f"claude noop cursor-event sid={sid} keys={sorted(event.keys())}")
            return {}
    if not sid:
        log(f"{host} noop no-id keys={sorted(event.keys())}")
        return {}
    if event.get("stop_hook_active"):
        return {}
    if once_path(host, sid).exists():
        log(f"{host} {sid} noop once")
        return {}
    try:
        ct = load_ct()
        cfg = ct.load_config()
        locale = ct.locale_of(cfg)
        if host in ("cursor", "grok"):
            title, day = ct.cursor_title_and_mmdd(sid, cfg)
        elif host == "claude":
            title = ct.claude_current_title(sid)
            day = datetime.now(ZoneInfo(cfg["timezone"])).strftime("%m%d")
        else:
            return {}
        action, new_title = ct.decide(title, locale, day, sid)
        if action == "silent" and host == "claude" and new_title:
            written = ct.silent_stamp_claude(sid)
            log(f"{host} {sid} silent {title!r} -> {written!r}")
            return {}
        if action in ("silent", "followup"):
            # Cursor keeps the live title in memory; writing SQLite is overwritten
            # on stop. The only durable path is one model turn + rename_chat.
            if not mark_once(host, sid):
                return {}
            ready = new_title if action == "silent" else ""
            log(f"{host} {sid} followup {title!r} ready={ready!r}")
            text = followup_text(locale, host, ready)
            if host == "claude":
                return {"decision": "block", "reason": text}
            return {"followup_message": text}
        log(f"{host} {sid} noop {title!r}")
    except Exception as exc:  # never break the host
        log(f"{host} {sid} error {exc!r}")
        return {}
    return {}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="cursor")
    args = parser.parse_args()
    result = handle(args.host, stdin_json())
    print(json.dumps(result, ensure_ascii=False) if result else "{}")


if __name__ == "__main__":
    main()
