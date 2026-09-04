#!/usr/bin/env bash
set -euo pipefail

PURGE=0
if [[ "${1:-}" == "--purge" ]]; then
  PURGE=1
fi

remove_link() {
  local dest="$1"
  if [[ -L "$dest" ]]; then
    rm -f "$dest"
    echo "removed $dest"
  elif [[ -d "$dest" ]]; then
    echo "skip $dest (not a symlink)"
  fi
}

for name in chat-stamp chat-title; do
  remove_link "$HOME/.cursor/skills/$name"
  remove_link "$HOME/.claude/skills/$name"
  remove_link "$HOME/.codex/skills/$name"
  remove_link "$HOME/.agents/skills/$name"
  remove_link "$HOME/.grok/skills/$name"
  remove_link "$HOME/.gemini/skills/$name"
done
for cmd in tu tc au ac chat-stamp chat-stamp-all chat-title chat-title-all; do
  remove_link "$HOME/.cursor/commands/${cmd}.md"
done

ORCA_SUPPORT="$HOME/Library/Application Support/orca"
if [[ -d "$ORCA_SUPPORT" ]]; then
  shopt -s nullglob
  for dest in \
    "$ORCA_SUPPORT/codex-runtime-home/home/skills/chat-stamp" \
    "$ORCA_SUPPORT"/codex-accounts/*/home/skills/chat-stamp
  do
    remove_link "$dest"
  done
  shopt -u nullglob
fi

if [[ "$PURGE" -eq 1 ]]; then
  rm -rf "$HOME/.config/chat-stamp" "$HOME/.config/chat-title"
  echo "removed ~/.config/chat-stamp"
fi

echo "skill unlinked. clone at ~/.local/share/ChatStamp or your git checkout is unchanged."
echo "hooks were never overwritten; remove chat-stamp entries from hooks.json / settings.json yourself."
