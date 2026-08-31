#!/usr/bin/env sh
set -eu

python_cmd="${PYTHON:-python3}"
"$python_cmd" - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit("YouRich requires Python 3.11 or newer.")
PY

installed=0

if command -v claude >/dev/null 2>&1 || [ -d "$HOME/.claude" ]; then
  mkdir -p "$HOME/.claude/skills"
  rm -rf "$HOME/.claude/skills/yourich"
  cp -R skill/yourich "$HOME/.claude/skills/yourich"
  installed=1
  echo "Installed YouRich skill for Claude Code."
fi

if command -v codex >/dev/null 2>&1 || [ -d "$HOME/.codex" ]; then
  mkdir -p "$HOME/.codex/skills"
  rm -rf "$HOME/.codex/skills/yourich"
  cp -R skill/yourich "$HOME/.codex/skills/yourich"
  installed=1
  echo "Installed YouRich skill for Codex."
fi

if [ "$installed" -eq 0 ]; then
  echo "No Claude Code or Codex user directory detected. Skill source remains at skill/yourich."
fi
