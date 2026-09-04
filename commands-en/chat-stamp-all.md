---
name: chat-stamp-all
description: Same as /au. All chats. Each date = last updated.
---

# /chat-stamp-all

Same as `/au`. Rename all chats. Each date is that chat's last-updated time.

1. If the title is clear and matches locale, only wrap the format.
2. If unclear or the wrong language, use `userSnippet` (user messages) plus `snippet` (assistant wrap-up, code stripped).
3. If still unclear, keep the original title.

Rules: `~/.cursor/skills/chat-stamp/SKILL.md`
