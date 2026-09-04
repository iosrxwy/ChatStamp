---
name: tu
description: Rename this chat only. Date = last updated (today if you are still in it).
---

# /tu

Rename **this chat only**. `MMDD` comes from this chat's **last-updated** time (timezone from config, default `Asia/Shanghai`).

Then `rename_chat`:

1. If the current title already names the work, only wrap `MMDD | type | topic`.
2. If the title is unclear or the wrong language, read my messages and your wrap-up. Strip code and patches.
3. If it is still unclear, keep the original title.

Types: feat, design, fix, perf, release, explore, docs, research.  
English user → English topic. Do not mix languages. Title only.

Unclear titles look like: `Untitled`, `New Chat`, `TODO asdf`, `panic`, `npm ERR`, file paths, raw git commands.
