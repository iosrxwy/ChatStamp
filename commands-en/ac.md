---
name: ac
description: Rename all chats. Each date = that chat's created time.
---

# /ac

Rename **all chats**. Each `MMDD` is that chat's own **created** time (the day that chat was opened).

Rules: `~/.cursor/skills/chat-stamp/SKILL.md`

```bash
python3 ~/.cursor/skills/chat-stamp/scripts/chat_stamp.py export --host auto --date-source created --out /tmp/chat-stamp-export.json
```

1. If `titleClear` is true and the language matches locale, wrap the existing title.
2. If unclear or the wrong language, use `userSnippet` (user messages) plus `snippet` (assistant wrap-up, code already stripped).
3. If still unclear, keep the original title.

One locale for the batch. Do not mix languages.
