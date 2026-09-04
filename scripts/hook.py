#!/usr/bin/env python3
"""Optional Stop / SessionEnd hook. Does not invent titles."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ONCE = Path.home() / ".config" / "chat-stamp" / "once"


def stdin_json() -> dict:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def session_id(event: dict) -> str:
    for key in (
        "conversation_id",
        "conversationId",
        "session_id",
        "sessionId",
        "thread_id",
        "composerId",
    ):
        if event.get(key):
            return str(event[key])
    return os.environ.get("CURSOR_CONVERSATION_ID") or os.environ.get("CODEX_THREAD_ID") or ""


def load_ct():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import chat_stamp as ct

    return ct


def followup(locale: str) -> str:
    if locale == "en":
        return (
            "/tu Rename this chat only. If the current title already names the work, "
            "wrap it as MMDD | type | topic using last-updated time. "
            "If the title is a placeholder, use the assistant wrap-up only "
            "(strip code, do not re-analyze the task). "
            "Then rename_chat. Title only."
        )
    return (
        "/tu 只改当前标题。现成标题已能看出主题就套成 MMDD｜类型｜主题（日期用最后更新）并 rename_chat；"
        "标题看不出来只看 AI 回复里去掉代码后的总结，不要自己再分析任务或代码；还看不懂就保留原名。只改标题。"
    )


def already_formatted(host: str, sid: str, locale: str) -> bool:
    if not sid:
        return False
    try:
        ct = load_ct()
        if host in ("cursor", "grok"):
            return ct.is_formatted(ct.cursor_current_title(sid), locale)
    except Exception:
        return False
    return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="cursor")
    args = parser.parse_args()
    event = stdin_json()
    sid = session_id(event)
    try:
        ct = load_ct()
        locale = ct.locale_of(ct.load_config())
    except Exception:
        locale = "zh"
    try:
        ONCE.mkdir(parents=True, exist_ok=True)
    except OSError:
        print("{}")
        return
    marker = ONCE / f"{args.host}-{sid or 'unknown'}"
    if marker.exists() or event.get("stop_hook_active"):
        print("{}")
        return
    if already_formatted(args.host, sid, locale):
        print("{}")
        return
    try:
        marker.write_text("1\n")
    except OSError:
        print("{}")
        return
    if args.host == "codex":
        pending = Path.home() / ".config" / "chat-stamp" / "pending.jsonl"
        try:
            pending.parent.mkdir(parents=True, exist_ok=True)
            with pending.open("a") as fh:
                fh.write(json.dumps({"host": "codex", "id": sid}, ensure_ascii=False) + "\n")
        except OSError:
            pass
        print("{}")
        return
    if args.host == "claude":
        # Claude Code Stop hook: "block" keeps the turn going with `reason`
        # as the next instruction. stop_hook_active means we already did.
        if event.get("stop_hook_active"):
            print("{}")
            return
        print(
            json.dumps(
                {"decision": "block", "reason": followup(locale)},
                ensure_ascii=False,
            )
        )
        return
    print(json.dumps({"followup_message": followup(locale)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
