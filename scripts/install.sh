#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATE_SOURCE="updated"
INSTALL_HOOKS=1
TZ_NAME="Asia/Shanghai"
LOCALE="zh"

usage() {
  echo "Usage: scripts/install.sh [--date-source updated|created] [--locale zh|en] [--timezone Asia/Shanghai] [--hooks|--no-hooks]"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --date-source) DATE_SOURCE="${2:-}"; shift 2 ;;
    --timezone) TZ_NAME="${2:-}"; shift 2 ;;
    --locale) LOCALE="${2:-}"; shift 2 ;;
    --hooks) INSTALL_HOOKS=1; shift ;;
    --no-hooks) INSTALL_HOOKS=0; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown arg: $1" >&2; usage; exit 1 ;;
  esac
done

if [[ "$DATE_SOURCE" != "updated" && "$DATE_SOURCE" != "created" ]]; then
  echo "date-source must be updated or created" >&2
  exit 1
fi
if [[ "$LOCALE" != "zh" && "$LOCALE" != "en" ]]; then
  echo "locale must be zh or en" >&2
  exit 1
fi

if [[ -f "$HOME/.config/chat-title/config.json" && ! -f "$HOME/.config/chat-stamp/config.json" ]]; then
  mkdir -p "$HOME/.config/chat-stamp"
  cp -R "$HOME/.config/chat-title/." "$HOME/.config/chat-stamp/"
  echo "migrated ~/.config/chat-title -> ~/.config/chat-stamp"
fi
for old in \
  "$HOME/.cursor/skills/chat-title" \
  "$HOME/.claude/skills/chat-title" \
  "$HOME/.codex/skills/chat-title" \
  "$HOME/.agents/skills/chat-title" \
  "$HOME/.grok/skills/chat-title" \
  "$HOME/.gemini/skills/chat-title" \
  "$HOME/.cursor/commands/chat-title.md" \
  "$HOME/.cursor/commands/chat-title-all.md"
do
  if [[ -L "$old" ]]; then
    rm -f "$old"
    echo "removed leftover $old"
  fi
done

python3 "$ROOT/scripts/chat_stamp.py" init --date-source "$DATE_SOURCE" --timezone "$TZ_NAME" --locale "$LOCALE"

link_skill() {
  local dest="$1"
  mkdir -p "$(dirname "$dest")"
  if [[ -e "$dest" && ! -L "$dest" ]]; then
    echo "skip $dest (exists and is not a symlink; remove it yourself)" >&2
    return 0
  fi
  rm -f "$dest"
  ln -s "$ROOT" "$dest"
  echo "skill -> $dest"
}

link_skill "$HOME/.cursor/skills/chat-stamp"
link_skill "$HOME/.claude/skills/chat-stamp"
mkdir -p "$HOME/.codex/skills"
link_skill "$HOME/.codex/skills/chat-stamp"
mkdir -p "$HOME/.agents/skills"
link_skill "$HOME/.agents/skills/chat-stamp"

if [[ -d "$HOME/.grok" ]]; then
  mkdir -p "$HOME/.grok/skills"
  link_skill "$HOME/.grok/skills/chat-stamp"
fi
if [[ -d "$HOME/.gemini" ]]; then
  mkdir -p "$HOME/.gemini/skills"
  link_skill "$HOME/.gemini/skills/chat-stamp"
fi

ORCA_SUPPORT="$HOME/Library/Application Support/orca"
if [[ -d "$ORCA_SUPPORT" ]]; then
  shopt -s nullglob
  for dest in \
    "$ORCA_SUPPORT/codex-runtime-home/home/skills" \
    "$ORCA_SUPPORT"/codex-accounts/*/home/skills
  do
    mkdir -p "$dest"
    link_skill "$dest/chat-stamp"
  done
  shopt -u nullglob
fi

CMD_DIR="$ROOT/commands"
if [[ "$LOCALE" == "en" ]]; then
  CMD_DIR="$ROOT/commands-en"
fi
mkdir -p "$HOME/.cursor/commands"
for cmd in tu tc au ac chat-stamp chat-stamp-all; do
  ln -sfn "$CMD_DIR/${cmd}.md" "$HOME/.cursor/commands/${cmd}.md"
  echo "command -> ~/.cursor/commands/${cmd}.md ($LOCALE)"
done

if [[ "$INSTALL_HOOKS" -eq 1 ]]; then
  python3 - "$ROOT" << 'PY'
import json, sys
from pathlib import Path
root = Path(sys.argv[1])
cmd = f'python3 "{root}/scripts/hook.py" --host cursor'
path = Path.home() / ".cursor/hooks.json"
data = {"version": 1, "hooks": {}}
if path.exists():
    data = json.loads(path.read_text())
stops = data.setdefault("hooks", {}).setdefault("stop", [])
updated = False
for item in stops:
    if not isinstance(item, dict):
        continue
    old = item.get("command", "")
    if "hook.py" in old and "--host cursor" in old and old != cmd:
        item["command"] = cmd
        updated = True
if updated:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print(f"updated stop hook path -> {path}")
elif not any("hook.py" in x.get("command", "") and "--host cursor" in x.get("command", "")
             for x in stops if isinstance(x, dict)):
    stops.append({"command": cmd, "timeout": 8})
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print(f"merged stop hook -> {path}")
else:
    print(f"stop hook already present -> {path}")

# Claude Code: two-phase Stop hook (silent wrap, else one block followup).
claude_dir = Path.home() / ".claude"
if claude_dir.is_dir():
    spath = claude_dir / "settings.json"
    settings = {}
    if spath.exists():
        try:
            settings = json.loads(spath.read_text())
        except json.JSONDecodeError:
            settings = None
    if settings is None:
        print(f"skip {spath}: not valid JSON, merge hooks/claude.settings.json by hand")
    else:
        ccmd = f'python3 "{root}/scripts/hook.py" --host claude'
        stop = settings.setdefault("hooks", {}).setdefault("Stop", [])
        present = False
        changed = False
        for group in stop:
            if not isinstance(group, dict):
                continue
            for h in group.get("hooks", []) if isinstance(group.get("hooks"), list) else []:
                if not isinstance(h, dict):
                    continue
                old = h.get("command", "")
                if "hook.py" not in old:
                    continue
                present = True
                if old != ccmd:
                    h["command"] = ccmd
                    changed = True
        if changed:
            spath.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + "\n")
            print(f"updated Stop hook path -> {spath}")
        elif not present:
            stop.append({"hooks": [{"type": "command", "command": ccmd, "timeout": 8}]})
            spath.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + "\n")
            print(f"merged Stop hook -> {spath}")
        else:
            print(f"Stop hook already present -> {spath}")
print("did not touch Orca/rtk hooks or ~/.codex/hooks.json")
PY
fi

echo "dateSource=$DATE_SOURCE locale=$LOCALE timezone=$TZ_NAME"
echo "auto: hook sends one short /tu followup (rename_chat). manual: /tu /tc /au /ac"
echo "done"
