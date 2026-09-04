#!/usr/bin/env python3
"""Export / apply conversation titles. Title text is chosen by the agent."""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TYPES_ZH = ("功能", "设计", "修复", "优化", "发布", "探索", "文档", "研究")
TYPES_EN = ("feat", "design", "fix", "perf", "release", "explore", "docs", "research")
TYPES = TYPES_ZH
HOME = Path.home()
CONFIG_DIR = HOME / ".config" / "chat-stamp"
DEFAULT_CONFIG = {
    "dateSource": "updated",
    "timezone": "Asia/Shanghai",
    "locale": "zh",
    "titleLanguage": "user",
    "titleFormat": "{mmdd}｜{type}｜{topic}",
    "types": list(TYPES_ZH),
    "typesZh": list(TYPES_ZH),
    "typesEn": list(TYPES_EN),
    "emptyAction": "archive",
    "emptyMaxBubbles": 1,
    "emptyMaxBodyChars": 8,
    "skipSubagents": True,
    "titleOnly": True,
}

_TYPE_ALT = "|".join(TYPES_ZH + TYPES_EN)
TITLE_RE = re.compile(
    rf"^(\d{{4}})\s*[|｜]\s*({_TYPE_ALT})\s*[|｜]\s*(.+)$"
)
FMT_RE = TITLE_RE


def locale_of(cfg: dict) -> str:
    loc = (cfg.get("locale") or "zh").lower()
    return loc if loc in ("zh", "en") else "zh"


def types_for(locale: str) -> tuple[str, ...]:
    return TYPES_EN if locale == "en" else TYPES_ZH


def sep_for(locale: str) -> str:
    return " | " if locale == "en" else "｜"


def topic_is_english_phrase(topic: str) -> bool:
    if re.search(r"[\u4e00-\u9fff]", topic):
        return False
    return len(re.sub(r"[^A-Za-z]", "", topic)) >= 6


def topic_has_cjk(topic: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", topic))


def title_ok_for_locale(title: str, locale: str) -> tuple[bool, str]:
    text = (title or "").strip()
    m = TITLE_RE.match(text)
    if not m:
        return False, "not-formatted"
    typ, topic = m.group(2), m.group(3).strip()
    if locale == "zh":
        if typ not in TYPES_ZH:
            return False, "english-type"
        if topic_is_english_phrase(topic):
            return False, "english-topic"
        return True, ""
    if typ not in TYPES_EN:
        return False, "chinese-type"
    if topic_has_cjk(topic):
        return False, "chinese-topic"
    return True, ""


def is_formatted(title: str, locale: str) -> bool:
    ok, _ = title_ok_for_locale(title, locale)
    return ok


_UNCLEAR_PREFIXES = (
    "untitled",
    "new chat",
    "new conversation",
    "new thread",
    "new session",
    "npm err",
    "pnpm err",
    "yarn err",
    "panic",
    "exc_",
    "error:",
    "fatal:",
    "debug-",
    "git ",
)
_UNCLEAR_EXACT = frozenset(
    ("todo", "test", "asdf", "foo", "bar", "tmp", "untitled", "chat")
)
_PATHISH = re.compile(r"^(?:[./~]|[A-Za-z]:\\)|.*\.(?:py|log|txt|json|ips|crash)$", re.I)


def title_is_clear(title: str) -> bool:
    """True when the sidebar title already names the work."""
    text = (title or "").strip()
    if not text:
        return False
    if TITLE_RE.match(text):
        return True
    low = text.lower()
    if low in _UNCLEAR_EXACT:
        return False
    if low.startswith("todo") and not topic_has_cjk(text):
        return False
    if any(low.startswith(prefix) for prefix in _UNCLEAR_PREFIXES):
        return False
    if _PATHISH.match(text):
        return False
    if topic_has_cjk(text):
        return True
    words = re.findall(r"[A-Za-z0-9]{2,}", text)
    return len(words) >= 2


def finalize_export_item(item: dict) -> dict:
    title = (item.get("title") or "").strip()
    locale = item.get("locale") or "zh"
    item["title"] = title
    item["formatted"] = is_formatted(title, locale)
    item["titleClear"] = title_is_clear(title)
    return item


def load_config() -> dict:
    path = CONFIG_DIR / "config.json"
    data = dict(DEFAULT_CONFIG)
    if path.exists():
        data.update(json.loads(path.read_text()))
    return data


def save_config(data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    path = CONFIG_DIR / "config.json"
    merged = load_config()
    merged.update(data)
    path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n")


def detect_host() -> str:
    hint = os.environ.get("CHAT_STAMP_HOST") or os.environ.get("CURSOR_TRACE_ID")
    if os.environ.get("ORCA_PANE_KEY") or os.environ.get("ORCA_AGENT_HOOK_ENV"):
        return "orca"
    if os.environ.get("CURSOR_TRACE_ID") or os.environ.get("CURSOR_PROJECT_DIR"):
        return "cursor"
    if os.environ.get("CLAUDE_PROJECT_DIR") or os.environ.get("CLAUDECODE"):
        return "claude"
    if os.environ.get("CODEX_HOME") or os.environ.get("CODEX_THREAD_ID"):
        return "codex"
    if hint:
        return "cursor"
    if (cursor_global_storage() / "state.vscdb").exists():
        return "cursor"
    if (HOME / ".codex/session_index.jsonl").exists():
        return "codex"
    if (HOME / ".claude/projects").exists():
        return "claude"
    return "cursor"


def mmdd(ts, tz_name: str, source_ms: bool = True) -> str | None:
    if ts is None:
        return None
    try:
        val = float(ts)
    except (TypeError, ValueError):
        if isinstance(ts, str) and ts:
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                return dt.astimezone(ZoneInfo(tz_name)).strftime("%m%d")
            except ValueError:
                return None
        return None
    if val > 1e12:
        val /= 1000.0
    if val < 1e9:
        return None
    return datetime.fromtimestamp(val, tz=ZoneInfo(tz_name)).strftime("%m%d")


def iso_to_ms(text: str | None) -> int | None:
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return int(dt.timestamp() * 1000)
    except ValueError:
        return None


# --- Cursor -----------------------------------------------------------------

def cursor_global_storage() -> Path:
    """Cursor user data dir: macOS, Linux, Windows; CURSOR_USER_DATA overrides."""
    override = os.environ.get("CURSOR_USER_DATA")
    if override:
        return Path(override).expanduser() / "User" / "globalStorage"
    candidates = [
        HOME / "Library/Application Support/Cursor/User/globalStorage",
        HOME / ".config/Cursor/User/globalStorage",
    ]
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidates.append(Path(appdata) / "Cursor/User/globalStorage")
    for root in candidates:
        if (root / "state.vscdb").exists():
            return root
    return candidates[0]


def cursor_paths() -> tuple[Path, Path]:
    root = cursor_global_storage()
    return root / "state.vscdb", root / "conversation-search.db"


def cursor_export(cfg: dict) -> list[dict]:
    state_path, search_path = cursor_paths()
    if not state_path.exists():
        return []
    state = sqlite3.connect(f"file:{state_path}?mode=ro", uri=True)
    bodies: dict[str, str] = {}
    if search_path.exists():
        search = sqlite3.connect(f"file:{search_path}?mode=ro", uri=True)
        for cid, body in search.execute(
            "SELECT c.id, substr(f.body,1,800) FROM conversations c "
            "LEFT JOIN conversation_fts f ON f.rowid=c.fts_rowid"
        ):
            bodies[cid] = body or ""
        search.close()
    rows = state.execute(
        "SELECT composerId, workspaceId, isArchived, isSubagent, createdAt, "
        "lastUpdatedAt, value FROM composerHeaders"
    ).fetchall()
    skip_sub = cfg.get("skipSubagents", True)
    locale = locale_of(cfg)
    out = []
    for cid, ws, arch, sub, created, updated, raw in rows:
        if skip_sub and sub:
            continue
        try:
            val = json.loads(raw)
        except Exception:
            continue
        created_ms = created or val.get("createdAt")
        updated_ms = updated or val.get("lastUpdatedAt")
        src = created_ms if cfg.get("dateSource") == "created" else updated_ms
        out.append(
            finalize_export_item(
                {
                    "host": "cursor",
                    "id": cid,
                    "title": (val.get("name") or "").strip(),
                    "workspaceId": ws,
                    "isArchived": bool(arch),
                    "isSubagent": bool(sub),
                    "createdAt": created_ms,
                    "updatedAt": updated_ms,
                    "locale": locale,
                    "mmdd": mmdd(src, cfg["timezone"]),
                    "snippet": assistant_summary_snippet(bodies.get(cid) or ""),
                }
            )
        )
    state.close()
    return out


def cursor_apply(items: list[dict]) -> int:
    state_path, search_path = cursor_paths()
    state = sqlite3.connect(str(state_path), timeout=60)
    search = sqlite3.connect(str(search_path), timeout=60) if search_path.exists() else None
    n = 0
    for item in items:
        cid, title = item["id"], item["title"]
        row = state.execute("SELECT value FROM composerHeaders WHERE composerId=?", (cid,)).fetchone()
        if not row:
            continue
        val = json.loads(row[0])
        if val.get("name") != title:
            val["name"] = title
            state.execute(
                "UPDATE composerHeaders SET value=? WHERE composerId=?",
                (json.dumps(val, ensure_ascii=False), cid),
            )
        key = f"composerData:{cid}"
        drow = state.execute("SELECT value FROM cursorDiskKV WHERE key=?", (key,)).fetchone()
        if drow:
            raw = drow[0]
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            data = json.loads(raw)
            if isinstance(data, dict) and data.get("name") != title:
                data["name"] = title
                state.execute(
                    "UPDATE cursorDiskKV SET value=? WHERE key=?",
                    (json.dumps(data, ensure_ascii=False), key),
                )
        if search:
            srow = search.execute(
                "SELECT fts_rowid, title FROM conversations WHERE id=?", (cid,)
            ).fetchone()
            if srow and srow[1] != title:
                search.execute("UPDATE conversations SET title=? WHERE id=?", (title, cid))
                try:
                    search.execute(
                        "UPDATE conversation_fts SET title=? WHERE rowid=?", (title, srow[0])
                    )
                except sqlite3.OperationalError:
                    pass
        n += 1
    state.commit()
    if search:
        search.commit()
        search.close()
    state.close()
    return n


def cursor_archive_empty(cfg: dict) -> int:
    state_path, search_path = cursor_paths()
    state = sqlite3.connect(str(state_path), timeout=60)
    search = sqlite3.connect(f"file:{search_path}?mode=ro", uri=True) if search_path.exists() else None
    bodies = {}
    if search:
        for cid, body in search.execute(
            "SELECT c.id, f.body FROM conversations c "
            "LEFT JOIN conversation_fts f ON f.rowid=c.fts_rowid"
        ):
            bodies[cid] = body or ""
        search.close()
    counts: dict[str, int] = {}
    for (key,) in state.execute("SELECT key FROM cursorDiskKV WHERE key LIKE 'bubbleId:%'"):
        parts = key.split(":", 2)
        if len(parts) >= 2:
            counts[parts[1]] = counts.get(parts[1], 0) + 1
    max_b = int(cfg.get("emptyMaxBubbles", 1))
    max_c = int(cfg.get("emptyMaxBodyChars", 8))
    n = 0
    rows = state.execute(
        "SELECT composerId, value FROM composerHeaders WHERE isSubagent=0 AND isArchived=0"
    ).fetchall()
    write_search = sqlite3.connect(str(search_path), timeout=60) if search_path.exists() else None
    for cid, raw in rows:
        val = json.loads(raw)
        name = (val.get("name") or "").strip()
        if name:
            continue
        snippet = re.sub(r"\s+", " ", bodies.get(cid, "")).strip()
        if counts.get(cid, 0) <= max_b and len(snippet) <= max_c:
            val["isArchived"] = True
            state.execute(
                "UPDATE composerHeaders SET isArchived=1, value=? WHERE composerId=?",
                (json.dumps(val, ensure_ascii=False), cid),
            )
            if write_search:
                write_search.execute(
                    "UPDATE conversations SET is_archived=1 WHERE id=?", (cid,)
                )
            n += 1
    state.commit()
    if write_search:
        write_search.commit()
        write_search.close()
    state.close()
    return n


def cursor_current_title(composer_id: str) -> str:
    state_path, _ = cursor_paths()
    con = sqlite3.connect(f"file:{state_path}?mode=ro", uri=True)
    row = con.execute(
        "SELECT json_extract(value,'$.name') FROM composerHeaders WHERE composerId=?",
        (composer_id,),
    ).fetchone()
    con.close()
    return (row[0] or "") if row else ""


# --- Codex ------------------------------------------------------------------

def codex_index() -> Path:
    return Path(os.environ.get("CODEX_HOME", HOME / ".codex")) / "session_index.jsonl"


def _rewrite_jsonl(path: Path, rewrite) -> None:
    lines = path.read_text().splitlines()
    out = []
    for line in lines:
        if not line.strip():
            continue
        obj = json.loads(line)
        obj = rewrite(obj)
        out.append(json.dumps(obj, ensure_ascii=False))
    path.write_text("\n".join(out) + ("\n" if out else ""))


_FENCE_RE = re.compile(r"```[\s\S]*?```")
_TILDE_FENCE_RE = re.compile(r"~~~[\s\S]*?~~~")
_HTML_PRE_RE = re.compile(r"<pre[\s\S]*?</pre>", re.I)
_HTML_CODE_RE = re.compile(r"<code[\s\S]*?</code>", re.I)
_INLINE_CODE_RE = re.compile(r"`[^`\n]{1,200}`")


def strip_code_blocks(text: str) -> str:
    text = text or ""
    text = _FENCE_RE.sub("\n\n", text)
    text = _TILDE_FENCE_RE.sub("\n\n", text)
    text = _HTML_PRE_RE.sub("\n\n", text)
    text = _HTML_CODE_RE.sub(" ", text)
    text = _INLINE_CODE_RE.sub(" ", text)
    return text


def _looks_like_code_line(line: str) -> bool:
    s = line.strip()
    if not s or s.startswith("<command-"):
        return True
    if s.startswith(
        (
            "def ",
            "class ",
            "import ",
            "from ",
            "func ",
            "let ",
            "const ",
            "var ",
            "#include",
            "#!/",
        )
    ):
        return True
    if s.endswith("{") or s.endswith("};") or s.endswith(");"):
        return True
    symbols = len(re.findall(r"[{}\[\]();=<>]", s))
    return symbols >= 4 and symbols / max(len(s), 1) > 0.14


def prose_paragraphs(text: str) -> list[str]:
    stripped = strip_code_blocks(text)
    paras = []
    for raw in re.split(r"\n{2,}", stripped):
        lines = [
            ln for ln in raw.splitlines() if ln.strip() and not _looks_like_code_line(ln)
        ]
        part = re.sub(r"\s+", " ", " ".join(lines)).strip()
        if len(part) < 8:
            continue
        paras.append(part)
    return paras


def assistant_summary_snippet(text: str, limit: int = 800) -> str:
    """Keep the wrap-up prose from an assistant reply; drop code."""
    paras = prose_paragraphs(text)
    if not paras:
        return ""
    return _join_snippet(paras[-3:], limit)


def _clip_snippet_part(text: str, limit: int = 240) -> str:
    cleaned = assistant_summary_snippet(text, limit)
    if not cleaned or "<command-" in cleaned:
        return ""
    return cleaned[:limit]


def _join_snippet(parts: list[str], limit: int = 800) -> str:
    out = []
    used = 0
    for part in parts:
        if used >= limit:
            break
        chunk = part[: max(0, limit - used)]
        if not chunk:
            continue
        out.append(chunk)
        used += len(chunk)
    return "\n".join(out)


def _codex_snippet(session_id: str) -> str:
    root = Path(os.environ.get("CODEX_HOME", HOME / ".codex")) / "sessions"
    if not root.exists():
        return ""
    for path in root.rglob(f"*{session_id}*.jsonl"):
        texts = []
        try:
            for line in path.read_text().splitlines()[:200]:
                if not any(
                    marker in line
                    for marker in ('"role":"assistant"', '"type":"assistant"')
                ):
                    continue
                m = re.search(r'"text"\s*:\s*"((?:\\.|[^"\\]){8,240})"', line)
                if m:
                    part = _clip_snippet_part(
                        bytes(m.group(1), "utf-8").decode("unicode_escape")
                    )
                    if part:
                        texts.append(part)
                if len(_join_snippet(texts)) >= 800:
                    break
        except OSError:
            return ""
        return _join_snippet(texts)
    return ""


def codex_export(cfg: dict) -> list[dict]:
    path = codex_index()
    if not path.exists():
        return []
    locale = locale_of(cfg)
    out = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        sid = obj.get("id") or ""
        updated = obj.get("updated_at")
        created = obj.get("created_at") or updated
        src = created if cfg.get("dateSource") == "created" else updated
        title = (obj.get("thread_name") or obj.get("title") or "").strip()
        out.append(
            finalize_export_item(
                {
                    "host": "codex",
                    "id": sid,
                    "title": title,
                    "createdAt": created,
                    "updatedAt": updated,
                    "locale": locale,
                    "mmdd": mmdd(iso_to_ms(src) if isinstance(src, str) else src, cfg["timezone"]),
                    "snippet": _codex_snippet(sid),
                    "isArchived": bool(obj.get("archived")),
                }
            )
        )
    return out


def codex_apply(items: list[dict]) -> int:
    path = codex_index()
    if not path.exists():
        return 0
    by_id = {i["id"]: i["title"] for i in items}
    n = 0

    def rewrite(obj):
        nonlocal n
        sid = obj.get("id")
        if sid in by_id:
            obj["thread_name"] = by_id[sid]
            n += 1
        return obj

    _rewrite_jsonl(path, rewrite)
    return n


# --- Claude -----------------------------------------------------------------

def claude_override_path() -> Path:
    return HOME / ".claude" / "chat-stamp-overrides.json"


def claude_export(cfg: dict) -> list[dict]:
    root = HOME / ".claude" / "projects"
    if not root.exists():
        return []
    overrides = {}
    op = claude_override_path()
    if op.exists():
        overrides = json.loads(op.read_text())
    locale = locale_of(cfg)
    out = []
    for path in root.rglob("*.jsonl"):
        if path.parent.name == "tool-results":
            continue
        sid = path.stem
        created = updated = None
        snippet_parts = []
        try:
            for i, line in enumerate(path.read_text().splitlines()):
                if not line.strip():
                    continue
                obj = json.loads(line)
                ts = obj.get("timestamp")
                if ts:
                    updated = ts
                    if created is None:
                        created = ts
                if obj.get("type") == "assistant" and len(_join_snippet(snippet_parts)) < 800:
                    msg = obj.get("message") or {}
                    content = msg.get("content")
                    text = content if isinstance(content, str) else ""
                    if isinstance(content, list):
                        text = " ".join(
                            c.get("text", "") for c in content if isinstance(c, dict)
                        )
                    part = _clip_snippet_part(text)
                    if part:
                        snippet_parts.append(part)
                if i > 400:
                    break
        except (OSError, json.JSONDecodeError):
            continue
        title = (overrides.get(sid) or {}).get("title") or ""
        src = created if cfg.get("dateSource") == "created" else updated
        out.append(
            finalize_export_item(
                {
                    "host": "claude",
                    "id": sid,
                    "title": title,
                    "createdAt": created,
                    "updatedAt": updated,
                    "locale": locale,
                    "mmdd": mmdd(iso_to_ms(src) if isinstance(src, str) else src, cfg["timezone"]),
                    "snippet": _join_snippet(snippet_parts),
                    "path": str(path),
                }
            )
        )
    return out


def claude_apply(items: list[dict]) -> int:
    op = claude_override_path()
    data = json.loads(op.read_text()) if op.exists() else {}
    for item in items:
        data[item["id"]] = {"title": item["title"]}
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    return len(items)


# --- Orca / Grok CLI -------------------------------------------------------

def orca_cache_path() -> Path:
    return HOME / "Library/Application Support/orca/ai-vault/session-parse-cache.json"


def grok_summary_path(session_id: str) -> Path | None:
    root = HOME / ".grok" / "sessions"
    if not session_id or not root.exists():
        return None
    direct = list(root.glob(f"**/{session_id}/summary.json"))
    if direct:
        return direct[0]
    for path in root.rglob("summary.json"):
        if session_id in path.parts:
            return path
    return None


def grok_set_title(session_id: str, title: str) -> bool:
    path = grok_summary_path(session_id)
    if not path:
        return False
    data = json.loads(path.read_text())
    data["generated_title"] = title
    if data.get("session_summary"):
        data["session_summary"] = title
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    return True


def orca_patch_cache(updates: dict[str, str]) -> int:
    path = orca_cache_path()
    if not path.exists() or not updates:
        return 0
    data = json.loads(path.read_text())
    n = 0
    entries = data.get("entries") or []
    for i, item in enumerate(entries):
        if not isinstance(item, list) or len(item) < 2:
            continue
        file_path, meta = item[0], item[1] or {}
        sess = meta.get("session") or {}
        sid = sess.get("sessionId") or ""
        title = updates.get(sid) or updates.get(file_path or "")
        if not title:
            continue
        if sess.get("title") != title:
            sess["title"] = title
            meta["session"] = sess
            entries[i] = [file_path, meta]
            n += 1
    if n:
        data["entries"] = entries
        path.write_text(json.dumps(data, ensure_ascii=False) + "\n")
    return n


def orca_export(cfg: dict) -> list[dict]:
    path = orca_cache_path()
    if not path.exists():
        return []
    locale = locale_of(cfg)
    out = []
    seen = set()
    data = json.loads(path.read_text())
    for item in data.get("entries") or []:
        if not isinstance(item, list) or len(item) < 2:
            continue
        file_path, meta = item[0], item[1] or {}
        sess = meta.get("session") or {}
        sid = sess.get("sessionId") or ""
        if not sid or sid in seen:
            continue
        seen.add(sid)
        engine = (sess.get("agent") or "unknown").lower()
        title = (sess.get("title") or "").strip()
        snippet = ""
        if engine == "grok":
            gp = grok_summary_path(sid)
            if gp:
                g = json.loads(gp.read_text())
                title = (g.get("generated_title") or g.get("session_summary") or title).strip()
                snippet = assistant_summary_snippet(g.get("last_turn_summary") or "")
        created = sess.get("createdAt")
        updated = sess.get("updatedAt") or sess.get("modifiedAt")
        src = created if cfg.get("dateSource") == "created" else updated
        out.append(
            finalize_export_item(
                {
                    "host": "orca",
                    "engine": engine,
                    "id": sid,
                    "title": title,
                    "createdAt": created,
                    "updatedAt": updated,
                    "locale": locale,
                    "mmdd": mmdd(iso_to_ms(src) if isinstance(src, str) else src, cfg["timezone"]),
                    "snippet": snippet or (sess.get("title") or "")[:200],
                    "path": file_path,
                }
            )
        )
    return out


def orca_apply(items: list[dict]) -> int:
    updates = {}
    n = 0
    for item in items:
        sid, title = item["id"], item["title"]
        engine = (item.get("engine") or "").lower()
        wrote = False
        if engine in ("cursor",):
            wrote = cursor_apply([item]) > 0
        elif engine in ("codex",):
            wrote = codex_apply([item]) > 0
        elif engine in ("claude",):
            wrote = claude_apply([item]) > 0
        elif engine in ("grok", "unknown", ""):
            grok_set_title(sid, title)
        updates[sid] = title
        if item.get("path"):
            updates[item["path"]] = title
        n += 1
    orca_patch_cache(updates)
    return n


def cursor_sync_names() -> int:
    """Copy composerHeaders.name onto composerData + search when they drifted."""
    state_path, search_path = cursor_paths()
    state = sqlite3.connect(str(state_path), timeout=60)
    search = sqlite3.connect(str(search_path), timeout=60) if search_path.exists() else None
    n = 0
    for cid, raw in state.execute(
        "SELECT composerId, value FROM composerHeaders WHERE isSubagent=0"
    ):
        header = (json.loads(raw).get("name") or "").strip()
        if not header:
            continue
        key = f"composerData:{cid}"
        drow = state.execute("SELECT value FROM cursorDiskKV WHERE key=?", (key,)).fetchone()
        if drow:
            rawd = drow[0]
            if isinstance(rawd, bytes):
                rawd = rawd.decode("utf-8")
            data = json.loads(rawd)
            if isinstance(data, dict) and (data.get("name") or "").strip() != header:
                data["name"] = header
                state.execute(
                    "UPDATE cursorDiskKV SET value=? WHERE key=?",
                    (json.dumps(data, ensure_ascii=False), key),
                )
                n += 1
        if search:
            srow = search.execute(
                "SELECT fts_rowid, title FROM conversations WHERE id=?", (cid,)
            ).fetchone()
            if srow and (srow[1] or "").strip() != header:
                search.execute("UPDATE conversations SET title=? WHERE id=?", (header, cid))
                try:
                    search.execute(
                        "UPDATE conversation_fts SET title=? WHERE rowid=?", (header, srow[0])
                    )
                except sqlite3.OperationalError:
                    pass
    state.commit()
    if search:
        search.commit()
        search.close()
    state.close()
    return n


HOSTS = {
    "cursor": (cursor_export, cursor_apply, cursor_archive_empty),
    "grok": (cursor_export, cursor_apply, cursor_archive_empty),
    "codex": (codex_export, codex_apply, lambda cfg: 0),
    "claude": (claude_export, claude_apply, lambda cfg: 0),
    "orca": (orca_export, orca_apply, lambda cfg: 0),
}


def cmd_init(args) -> None:
    locale = args.locale or "zh"
    save_config(
        {
            "dateSource": args.date_source,
            "timezone": args.timezone,
            "locale": locale,
            "titleLanguage": "user",
            "types": list(types_for(locale)),
            "titleFormat": "{mmdd} | {type} | {topic}"
            if locale == "en"
            else "{mmdd}｜{type}｜{topic}",
        }
    )
    print(CONFIG_DIR / "config.json")


def cmd_export(args) -> None:
    cfg = load_config()
    if args.date_source:
        cfg["dateSource"] = args.date_source
    if args.locale:
        cfg["locale"] = args.locale
    host = args.host if args.host != "auto" else detect_host()
    items = HOSTS[host][0](cfg)
    text = json.dumps(items, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n")
        print(args.out, len(items), f"locale={locale_of(cfg)}")
    else:
        print(text)


def filter_titles_for_locale(items: list[dict], locale: str) -> tuple[list[dict], int]:
    kept = []
    skipped = 0
    for item in items:
        title = (item.get("title") or "").strip()
        ok, reason = title_ok_for_locale(title, locale)
        if not ok:
            print(f"skip {item.get('id')}: {reason} {title}", file=sys.stderr)
            skipped += 1
            continue
        kept.append(item)
    return kept, skipped


def cmd_apply(args) -> None:
    cfg = load_config()
    if args.locale:
        cfg["locale"] = args.locale
    locale = locale_of(cfg)
    payload = json.loads(Path(args.map).read_text())
    if isinstance(payload, dict):
        payload = payload.get("items") or payload.get("map") or []
    by_host: dict[str, list] = {}
    skipped = 0
    for item in payload:
        host = item.get("host") or (args.host if args.host != "auto" else detect_host())
        by_host.setdefault(host, []).append(item)
    total = 0
    for host, items in by_host.items():
        kept, nskip = filter_titles_for_locale(items, locale)
        skipped += nskip
        if kept:
            total += HOSTS[host][1](kept)
    print(f"applied {total} skipped {skipped} locale={locale}")


def cmd_sync(args) -> None:
    host = args.host if args.host != "auto" else detect_host()
    if host in ("cursor", "grok"):
        print(f"synced {cursor_sync_names()}")
        return
    print("sync is only for cursor / grok-in-cursor")


def cmd_archive_empty(args) -> None:
    cfg = load_config()
    host = args.host if args.host != "auto" else detect_host()
    n = HOSTS[host][2](cfg)
    print(f"archived {n}")


def cmd_current(args) -> None:
    cfg = load_config()
    host = args.host if args.host != "auto" else detect_host()
    cid = args.id or os.environ.get("CURSOR_CONVERSATION_ID") or os.environ.get(
        "CODEX_THREAD_ID"
    )
    print(
        json.dumps(
            {"host": host, "id": cid, "dateSource": cfg.get("dateSource"), "config": cfg},
            ensure_ascii=False,
        )
    )


def main() -> None:
    p = argparse.ArgumentParser(description="Rename agent chats (title only).")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("init")
    s.add_argument("--date-source", choices=("created", "updated"), required=True)
    s.add_argument("--timezone", default="Asia/Shanghai")
    s.add_argument("--locale", choices=("zh", "en"), default="zh")
    s = sub.add_parser("export")
    s.add_argument("--host", default="auto")
    s.add_argument("--date-source", choices=("created", "updated"))
    s.add_argument("--locale", choices=("zh", "en"))
    s.add_argument("--out")
    s = sub.add_parser("apply")
    s.add_argument("--map", required=True)
    s.add_argument("--host", default="auto")
    s.add_argument("--locale", choices=("zh", "en"))
    s = sub.add_parser("archive-empty")
    s.add_argument("--host", default="auto")
    s = sub.add_parser("sync")
    s.add_argument("--host", default="auto")
    s = sub.add_parser("current")
    s.add_argument("--host", default="auto")
    s.add_argument("--id")
    args = p.parse_args()
    {"init": cmd_init, "export": cmd_export, "apply": cmd_apply,
     "archive-empty": cmd_archive_empty, "sync": cmd_sync,
     "current": cmd_current}[args.cmd](args)


if __name__ == "__main__":
    main()
