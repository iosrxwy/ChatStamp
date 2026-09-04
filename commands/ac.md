---
name: ac
description: 整理全部对话的标题。每条日期用该对话的创建时间。
---

# /ac

改**全部对话**的标题。每条的 `MMDD` 用**那一条自己的创建时间**（哪天开的那条用哪天）。

完整规则只读这一份：`~/.cursor/skills/chat-stamp/SKILL.md`

```bash
python3 ~/.cursor/skills/chat-stamp/scripts/chat_stamp.py export --host auto --date-source created --out /tmp/chat-stamp-export.json
```

`titleClear` 为真：套现成标题。为假：只看 `snippet` 里 AI 回复的总结（已去掉代码）。同一 locale。
