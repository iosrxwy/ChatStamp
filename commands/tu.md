---
name: tu
description: 只改当前这条对话的标题。日期用最后更新时间（还在聊就用今天）。
---

# /tu

只改**当前这一条**。`MMDD` 用这条对话的**最后更新时间**（时区默认 `Asia/Shanghai`）。

Cursor：`rename_chat`。Orca 里的 Grok 不要写 `--host claude`：用 `scripts/chat_stamp.py apply --host orca`（会钉标题并 `orca terminal rename` 改左边项目列表）。

然后：

1. 现成标题已经能看懂主题：只套成 `MMDD｜类型｜主题`。
2. 标题看不懂或语言不符（例如中文用户遇到英文标题）：看我发的消息和你的回复总结，去掉代码和补丁。
3. 还是看不懂：保留原名。

类型：功能、设计、修复、优化、发布、探索、文档、研究。  
中文用户写中文主题，不要中英混排。只改标题。

标题算看不懂的例子：`Untitled`、`New Chat`、`TODO asdf`、`panic`、`npm ERR`、文件路径、裸 git 命令。
