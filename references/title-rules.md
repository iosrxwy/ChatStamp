# Title rules

Decide in this order:

1. If the **current title** already names the work, keep that topic. Only wrap `MMDD｜类型｜` (or the English form).
2. If the title is a placeholder (`Untitled`, `New Chat`, `panic`, `npm ERR`, a path, a raw git line, `TODO asdf`), read only the **assistant wrap-up**. Strip code. Do not re-analyze the task or the patch.
3. If the theme is still unclear, keep the original title.

Write the title in the **user locale**. Do not transliterate an English sidebar title, and do not keep English when `locale=zh`.

## Title language

`titleLanguage` is always `user`. Locale is one value for the whole machine, not per chat.

| locale | Format | Types |
|--------|--------|-------|
| `zh` (default) | `MMDD｜类型｜主题` | 功能、设计、修复、优化、发布、探索、文档、研究 |
| `en` | `MMDD \| type \| topic` | feat, design, fix, perf, release, explore, docs, research |

- Chinese user / Chinese output → `zh`. Every title is Chinese, including chats whose messages are English.
- English titles only when the user set `locale=en`.
- Do not detect language from `snippet`.
- Unclear theme → keep the original title. Same model, more context if needed. No second model.

## Date

- `dateSource=updated` → last activity (`updatedAt` / `lastUpdatedAt` / file mtime).
- `dateSource=created` → first message or `createdAt`.
- Convert with the configured IANA timezone (default `Asia/Shanghai`).
- `MMDD` is month+day only.

## Type (`zh`)

Pick exactly one:

| Type | When |
|------|------|
| 功能 | New capability, settings, entry points |
| 设计 | Layout, UI, color, copy, placement |
| 修复 | Crash, bug, conflict, wrong behavior |
| 优化 | Perf, jank, delay, cleanup |
| 发布 | Build, pack, upload, release |
| 探索 | Advice-only, survey, “what is this” |
| 文档 | Rules, indexes, knowledge, comments-as-docs |
| 研究 | IDA, dSYM, protocol, comparison |

## Type (`en`)

| Type | When |
|------|------|
| feat | New capability, settings, entry points |
| design | Layout, UI, color, copy, placement |
| fix | Crash, bug, conflict, wrong behavior |
| perf | Perf, jank, delay, cleanup |
| release | Build, pack, upload, release |
| explore | Advice-only, survey, “what is this” |
| docs | Rules, indexes, knowledge, comments-as-docs |
| research | IDA, dSYM, protocol, comparison |

If the title already starts with a type word **in the user locale**, keep that type.

## Topic

- `zh`: 2–16 Chinese characters when possible. Topic must be Chinese. Short Latin tokens (IDA, dSYM, Hook, JSON) may stay inside a Chinese phrase.
- `en`: 3–6 words. Topic must be English.
- Prefer the existing title when `titleClear` is true. Otherwise use the assistant wrap-up in `snippet` (code already stripped).
- Strip project names (`WCRefine`, `WeChat` as a prefix, repo folder names).
- Drop paths, `.ips`, crash filenames, wxids, URLs.
- Questions like “什么原因闪退” with no feature → `崩溃日志` only when the user actually attached a crash / asked to analyze a crash.
- If still unclear → keep the original title.

## Empty chats

Archive when there is no real user text (no bubbles, or only whitespace / a single digit / `?`). FTS empty ≠ chat empty.

## Forbidden edits

Do not change project name, message bodies, workspace affiliation, sort/recency, or pin. Archive is allowed only for empty chats, or when the user explicitly asks.
