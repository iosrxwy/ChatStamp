#!/usr/bin/env bash
# One-line install: curl -fsSL .../bootstrap.sh | bash -s -- --locale zh
set -euo pipefail

DEST="${CHAT_STAMP_HOME:-$HOME/.local/share/ChatStamp}"
REPO="${CHAT_STAMP_REPO:-https://github.com/iosrxwy/ChatStamp.git}"

if [[ -d "$DEST/.git" ]]; then
  git -C "$DEST" pull --ff-only
else
  mkdir -p "$(dirname "$DEST")"
  git clone --depth 1 "$REPO" "$DEST"
fi

exec "$DEST/scripts/install.sh" "$@"
