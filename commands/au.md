---
name: au
description: 整理全部对话的标题。每条日期用该对话的最后更新时间。
---

# /au

改**全部对话**的标题。每条的 `MMDD` 用**那一条自己的最后更新时间**。

完整规则只读这一份：`~/.cursor/skills/chat-stamp/SKILL.md`

```bash
python3 ~/.cursor/skills/chat-stamp/scripts/chat_stamp.py export --host auto --date-source updated --out /tmp/chat-stamp-export.json
```

`titleClear` 为真：套现成标题。为假：只看 `snippet` 里 AI 回复的总结（已去掉代码）。同一 locale。
