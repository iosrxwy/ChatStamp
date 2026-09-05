---
name: chat-stamp
description: >-
  Renames local agent chats to MMDD｜类型｜主题 (zh) or MMDD | type | topic (en).
  Prefers an existing clear title and only wraps the format. If the title
  is unclear or the wrong language, uses the user's messages plus the
  assistant wrap-up (code stripped). Use when the user types /tu /tc /au /ac,
  /chat-stamp, or asks to organize sidebar titles / 对话重命名.
argument-hint: /tu /tc /au /ac
license: MIT
metadata:
  author: iosrxwy
  version: "1.6.0"
---

# ChatStamp

Portable Agent Skill. Humans install from [README.md](README.md).

## Tokens

| Token | 改谁 | 标题里的日期 |
|-------|------|----------------|
| `/tu` | 只改当前这条 | 这条的最后更新时间（还在聊就用今天） |
| `/tc` | 只改当前这条 | 这条的创建时间（哪天开的用哪天） |
| `/au` | 全部对话 | 各条用自己的最后更新时间 |
| `/ac` | 全部对话 | 各条用自己的创建时间 |

`/chat-stamp` → `/tu`. `/chat-stamp all` → `/au`.

`/tu` and `/tc` use the conversation already on screen. The command file is the full instruction; there is no extra file to discover.

`/au` and `/ac` read this `SKILL.md` at `~/.cursor/skills/chat-stamp/SKILL.md` (or the install path) and run `scripts/chat_stamp.py`.

## How to pick a title

1. If the **current title** already names the work and matches the locale, keep that topic. Only wrap `MMDD｜类型｜` (or the English form).
2. If the title is unclear, empty, or the wrong language (e.g. English title when `locale=zh`), read the **user messages** and the **assistant wrap-up** (结论 / 已改成 / Summary). Strip code fences and patches.
3. If the theme is still unclear, keep the original title. Do not use another model.

Chinese user / `locale=zh` → Chinese type and topic, even when the body is English.  
`locale=en` → English type and topic. Never mix the two.

Types (`zh`): 功能、设计、修复、优化、发布、探索、文档、研究.  
Types (`en`): feat, design, fix, perf, release, explore, docs, research.

```
现成标题：优化批次文字显示
结果：0903｜优化｜批次文字显示

现成标题：Untitled-1 / ImgPlayCrack analysis
看用户消息 + AI 总结（去代码）后再 rename_chat
```

Title only. Do not change project, messages, pin, sort, or workspace.

## Config (ask once)

`~/.config/chat-stamp/config.json`

- `dateSource`: `updated` (default) or `created`. A token overrides this turn.
- `locale`: `zh` if the user writes Chinese; `en` only when they ask for English titles.
- `timezone`: default `Asia/Shanghai`.

## Batch workflow (`/au` `/ac`)

```bash
python3 ~/.cursor/skills/chat-stamp/scripts/chat_stamp.py export --host auto --out /tmp/chat-stamp-export.json
python3 ~/.cursor/skills/chat-stamp/scripts/chat_stamp.py apply --map /tmp/chat-stamp-map.json
python3 ~/.cursor/skills/chat-stamp/scripts/chat_stamp.py archive-empty --host auto
```

Export sets `titleClear`, `snippet` (assistant wrap-up, code stripped), and `userSnippet` (leading user text, paths/code stripped, ≤400). Cursor FTS `body` has no role markers, so `userSnippet` may include both sides. When `titleClear` is true, wrap the existing title. When false or the language does not match locale, use `userSnippet` plus `snippet`.  
Map: `[{"id":"<id>","title":"0904｜修复｜注入闪退"}]`

Current Cursor chat: `rename_chat`, then `apply` for that id so the composer store matches the sidebar.

More type tables: [references/title-rules.md](references/title-rules.md).

## Hosts

| Host | Where the title is written |
|------|----------------------------|
| Cursor / Grok-in-Cursor | `composerHeaders` + `composerData` + search `title` |
| Codex | `thread_name` in `session_index.jsonl` |
| Claude Code | `~/.claude/chat-stamp-overrides.json` |
| Orca + Grok TUI | Grok `summary.json` (`title_is_manual`) + session cache + `orca terminal rename` (`customTitle`, left project list) |
| Other IDEs | whatever that client uses after loading this skill |

`--host auto|cursor|grok|codex|claude|orca`

## Hook

`scripts/install.sh` merges a Cursor `stop` hook and a Claude `Stop` hook. Cursor cannot silently rename the live sidebar; the hook sends one short followup so the model can `rename_chat` (the finished title is included when the current name already wraps). Cursor also runs Claude Stop hooks; those are skipped when the id is a Cursor composer. Grok TUI also loads `~/.claude/settings.json` Stop hooks: if `GROK_SESSION_ID` is set, the hook never writes Claude overrides and never asks for `--host claude`. It silently wraps when it can, otherwise one followup with `--host orca` (that apply also runs `orca terminal rename`). Each conversation is followed up at most once (`~/.config/chat-stamp/once/{host}-{id}`). Codex SessionEnd only records an id. Existing Orca/rtk hooks are left as they are.

## Safety

- Archive empty chats only (`emptyMaxBubbles` / `emptyMaxBodyChars`).
- Do not put secrets from transcripts into titles.
- One locale for the whole machine, not per chat.
