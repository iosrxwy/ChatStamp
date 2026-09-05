# Hooks

Hooks are optional. The skill can run when the user types `/tu` `/tc` `/au` `/ac`.

`scripts/install.sh` **merges** a Cursor `stop` hook into `~/.cursor/hooks.json`, and a Claude Code `Stop` hook into `~/.claude/settings.json` when `~/.claude` exists. It does not overwrite Orca, rtk, or other existing entries. Use `--no-hooks` to skip.

The hook does not invent titles by itself. Cursor keeps the live sidebar title in memory, so writing SQLite on `stop` is overwritten. The durable path is **one** short followup so the model can `rename_chat`. If the current title already wraps cleanly, that followup contains the finished title. If it is unclear, empty, or the wrong language, the model reads the chat. Each conversation is followed up at most once: `~/.config/chat-stamp/once/{host}-{id}`. Cursor also runs `~/.claude` Stop hooks; those are skipped when the id is a Cursor composer. `uninstall.sh --purge` removes that directory with the rest of `~/.config/chat-stamp`.

The JSON fragments in this folder use `$CHAT_STAMP_HOME` as the checkout path (`~/.local/share/ChatStamp` after `bootstrap.sh`). When merging by hand, either export that variable for the host or replace it with the absolute path. `install.sh` writes the absolute path for Cursor.

## Cursor / Grok-in-Cursor

Event: `stop`.

`hooks/cursor.hooks.json` calls `scripts/hook.py --host cursor`.

- Already formatted → `{}`.
- Clear title that wraps and passes `title_ok_for_locale` → one `followup_message` with that finished title.
- Otherwise → one `followup_message` asking the model to read the chat. No conversation id → `{}`.

The hook never guesses “the most recently updated chat”.

## Claude Code

Event: `Stop` (and optional `SessionEnd`).

`hooks/claude.settings.json` is what `install.sh` merges into `~/.claude/settings.json`. If the id exists in Cursor's composer store, return `{}` (Cursor is replaying this Stop). Silent wrap only if `~/.claude/chat-stamp-overrides.json` already has a title. Otherwise one `{"decision":"block","reason":"<short followup>"}`. `stop_hook_active` → `{}`.

## Codex

Event: `SessionEnd`.

`hooks/codex.hooks.json` is advisory and time-capped. It only records the session id in `~/.config/chat-stamp/pending.jsonl`. If `~/.codex/hooks` already has another auto-title script, `install.sh` does not add a second one.

## Grok

When Grok runs inside Cursor, use the Cursor hook.

Grok TUI also loads `~/.claude/settings.json` Stop hooks. If `GROK_SESSION_ID` / `GROK_AGENT` is set, `hook.py` ignores `--host claude`: it never writes `chat-stamp-overrides.json` and never asks the model for `--host claude`. Clear Chinese titles wrap silently (pin `title_is_manual`, patch the Orca cache, `orca terminal rename` so the left project list updates). Unclear titles get one `block` followup that says `--host orca`.

The Orca left sidebar reads tab `customTitle`, not Grok `generated_title`. `apply --host orca` must call `orca terminal rename`; writing `summary.json` alone does not change that list.
