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

1. `titleClear` 为真且语言符合 locale：只套现成标题。
2. 看不懂或语言不符：看 `userSnippet`（用户消息）和 `snippet`（AI 总结，已去代码）。
3. 还是看不懂：保留原名。

同一 locale，不要中英混排。
