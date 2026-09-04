#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import chat_stamp as ct


def ok(title, locale):
    passed, reason = ct.title_ok_for_locale(title, locale)
    assert passed, f"{locale!r} {title!r} -> {reason}"


def no(title, locale, why):
    passed, reason = ct.title_ok_for_locale(title, locale)
    assert not passed, f"{locale!r} {title!r} should fail"
    assert reason == why, f"{title!r} expected {why}, got {reason}"


ok("0904｜修复｜注入闪退", "zh")
ok("0903｜优化｜批次文字显示", "zh")
ok("0904｜研究｜dSYM", "zh")
ok("0904 | fix | inject crash", "en")
ok("0904｜feat｜sidebar stamp", "en")

no("0904 | fix | inject crash", "zh", "english-type")
no("0904｜修复｜inject crash", "zh", "english-topic")
no("Voice transcription", "zh", "not-formatted")
no("0904｜修复｜注入闪退", "en", "chinese-type")
no("0904 | fix | 注入闪退", "en", "chinese-topic")

assert ct.locale_of({}) == "zh"
assert ct.locale_of({"locale": "en"}) == "en"
assert ct.locale_of({"locale": "de"}) == "zh"

assert ct.title_is_clear("优化批次文字显示")
assert ct.title_is_clear("0903｜优化｜批次文字显示")
assert ct.title_is_clear("Voice transcription")
assert ct.title_is_clear("TODO 列表整理")
assert not ct.title_is_clear("")
assert not ct.title_is_clear("Untitled-1")
assert not ct.title_is_clear("New Chat")
assert not ct.title_is_clear("TODO asdfasdf")
assert not ct.title_is_clear("panic: EXC_BAD_ACCESS")
assert not ct.title_is_clear("npm ERR! code EPERM")
assert not ct.title_is_clear("/Users/me/app/main.py")
assert not ct.title_is_clear("git push --force")

item = ct.finalize_export_item({"title": "Untitled-1", "locale": "zh"})
assert item["titleClear"] is False
assert item["formatted"] is False
item = ct.finalize_export_item({"title": "优化批次文字显示", "locale": "zh"})
assert item["titleClear"] is True

assert ct.guess_type("优化批次文字显示", "zh") == "优化"
assert ct.guess_type("inject crash", "en") == "fix"
assert ct.guess_type("random topic", "zh") == "探索"
assert ct.guess_type("prefix only", "en") == "explore"
assert ct.wrap_clear_title("优化批次文字显示", "0903", "zh") == "0903｜优化｜批次文字显示"
assert ct.wrap_clear_title("Voice transcription", "0903", "en") == "0903 | explore | Voice transcription"
assert ct.wrap_clear_title("Voice transcription", "0903", "zh") is None
assert ct.wrap_clear_title("Untitled-1", "0903", "zh") is None
assert ct.wrap_clear_title("0903｜优化｜批次文字显示", "0905", "zh") is None
assert ct.wrap_clear_title("0527｜功能｜GitHub commit", "0527", "zh") is None
assert ct.wrap_clear_title("inject crash", "0904", "en") == "0904 | fix | inject crash"
assert ct.wrap_clear_title("修复闪退", "0905", "zh") == "0905｜修复｜闪退"
assert ct.wrap_clear_title("designer tools", "0905", "en") == "0905 | explore | designer tools"
assert ct.wrap_clear_title("fixture cleanup", "0905", "en") == "0905 | explore | fixture cleanup"
assert ct.wrap_clear_title("ImgPlayCrack analysis", "0905", "zh") is None

assert ct.decide("0905｜修复｜闪退", "zh", "0905", "id1") == ("noop", None)
assert ct.decide("优化批次文字显示", "zh", "0903", "id1") == (
    "silent",
    "0903｜优化｜批次文字显示",
)
assert ct.decide("ImgPlayCrack analysis", "zh", "0905", "id1") == ("followup", None)
assert ct.decide("0527｜功能｜GitHub commit", "zh", "0527", "id1") == ("followup", None)
assert ct.decide("", "zh", "0905", "id1") == ("followup", None)
assert ct.decide("优化批次文字显示", "zh", "0903", "") == ("noop", None)

mixed = """先改口令说明。

```python
def rename(title):
    return title
```

已经改好：只看 AI 回复的总结，不读代码。
"""
snippet = ct.assistant_summary_snippet(mixed)
assert "def rename" not in snippet
assert "不读代码" in snippet
assert ct.assistant_summary_snippet("```js\nconsole.log(1)\n```") == ""

user_sn = ct.user_snippet_from_text(
    "看这边。\n```python\nprint(1)\n```\n/Users/me/app.py 继续"
)
assert "print(1)" not in user_sn
assert "/Users/me" not in user_sn
assert "看这边" in user_sn

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import hook as hk

assert hk.looks_like_cursor_event({"conversation_id": "abc"})
assert not hk.looks_like_cursor_event({"session_id": "abc", "hook_event_name": "Stop"})
assert not hk.looks_like_cursor_event(
    {"conversation_id": "abc", "session_id": "s", "hook_event_name": "Stop"}
)
print("ok")
