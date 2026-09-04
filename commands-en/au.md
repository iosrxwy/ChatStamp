---
name: au
description: Rename all chats. Each date = that chat's last-updated time.
---

# /au

Rename **all chats**. Each `MMDD` is that chat's own **last-updated** time.

Rules: `~/.cursor/skills/chat-stamp/SKILL.md`

```bash
python3 ~/.cursor/skills/chat-stamp/scripts/chat_stamp.py export --host auto --date-source updated --out /tmp/chat-stamp-export.json
```

If `titleClear` is true, wrap the existing title. If false, use the assistant wrap-up in `snippet` (code already stripped). One locale for the batch.
