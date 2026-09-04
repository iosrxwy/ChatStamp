# Hooks

Hooks are optional. The skill can run when the user types `/tu` `/tc` `/au` `/ac`.

`scripts/install.sh` **merges** a Cursor `stop` hook into `~/.cursor/hooks.json`, and a Claude Code `Stop` hook into `~/.claude/settings.json` when `~/.claude` exists. It does not overwrite Orca, rtk, or other existing entries. Use `--no-hooks` to skip.

The hook does not invent titles. If the current title is already formatted, it does nothing.

The JSON fragments in this folder use `$CHAT_STAMP_HOME` as the checkout path (`~/.local/share/ChatStamp` after `bootstrap.sh`). When merging by hand, either export that variable for the host or replace it with the absolute path. `install.sh` writes the absolute path for Cursor.

## Cursor / Grok-in-Cursor

Event: `stop`.

`hooks/cursor.hooks.json` calls `scripts/hook.py --host cursor`. If this chat is not already `MMDD｜类型｜主题` (or the English form), the hook returns one `followup_message`. That message is a self-contained `/tu`: use the existing title when it is clear; otherwise use the assistant wrap-up (code stripped), then `rename_chat`.

A marker under `~/.config/chat-stamp/once/` runs this at most once per conversation.

## Claude Code

Event: `Stop` (and optional `SessionEnd`).

`hooks/claude.settings.json` is what `install.sh` merges into `~/.claude/settings.json`. On `Stop`, if the title is not formatted, `hook.py --host claude` returns `{"decision":"block","reason":"/tu ..."}`, which makes Claude run one more turn with that instruction. `stop_hook_active` and the once-marker prevent a loop. `SessionEnd` only writes a pending note.

## Codex

Event: `SessionEnd`.

`hooks/codex.hooks.json` is advisory and time-capped. It only records the session id. If `~/.codex/hooks` already has another auto-title script, `install.sh` does not add a second one.

## Grok

When Grok runs inside Cursor, use the Cursor hook.
