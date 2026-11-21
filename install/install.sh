#!/usr/bin/env bash
# Install the powerbi-architect skill into a repository (or globally) for every major AI agent.
#
#   ./install/install.sh [TARGET_REPO] [--global] [--link] [--force] [--no-graph] [--no-hooks]
#   ./install/install.sh [TARGET_REPO] [--global] --status | --update
#
#   TARGET_REPO  repository to install into (default: current directory)
#   --global     install in your user folders instead (~/.claude, ~/.copilot, ~/.codex)
#   --link       symlink instead of copy (updates with `git pull` in this repo)
#   --force      replace an existing installation
#   --no-graph   only copy files: do not build the Power BI knowledge graph
#   --no-hooks   build the graph but do not add auto-refresh hooks (Claude Code, git)
#   --status     show the installed version in each destination and this copy's version; change nothing
#   --update     replace installations older than this copy (run `git pull` in this repo first)
#
# Destinations (project):  .claude/skills  (Claude Code, Cursor)
#                          .github/skills  (GitHub Copilot: VS Code agent mode, CLI, coding agent)
#                          .agents/skills  (OpenAI Codex and other Agent Skills readers)
# Nothing is downloaded. After copying, and only for a repository install, the installer runs the
# skill's own offline script (scripts/pbi_graph.py, Python stdlib) to build powerbi-graph/, add a short
# section to AGENTS.md/CLAUDE.md and add refresh hooks. Use --no-graph to skip that step.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$HERE/skills/powerbi-architect"
TARGET="."; GLOBAL=0; LINK=0; FORCE=0; GRAPH=1; HOOKS=1; STATUS=0; UPDATE=0
for arg in "$@"; do
  case "$arg" in
    --global) GLOBAL=1 ;;
    --link)   LINK=1 ;;
    --force)  FORCE=1 ;;
    --no-graph) GRAPH=0 ;;
    --no-hooks) HOOKS=0 ;;
    --status) STATUS=1 ;;
    --update) UPDATE=1 ;;
    -h|--help) sed -n '2,22p' "$0"; exit 0 ;;
    -*) echo "Unknown option: $arg (see --help)" >&2; exit 2 ;;
    *) TARGET="$arg" ;;
  esac
done
[ -f "$SRC/SKILL.md" ] || { echo "SKILL.md not found in $SRC" >&2; exit 1; }
version_of() { grep -m1 'version:' "$1/SKILL.md" 2>/dev/null | tr -d ' "' | cut -d: -f2; }
VERSION="$(version_of "$SRC")"

if [ "$GLOBAL" = 1 ]; then
  DESTS=("$HOME/.claude/skills" "$HOME/.copilot/skills" "$HOME/.codex/skills")
else
  [ -d "$TARGET" ] || { echo "Target folder not found: $TARGET" >&2; exit 1; }
  TARGET="$(cd "$TARGET" && pwd)"
  DESTS=("$TARGET/.claude/skills" "$TARGET/.github/skills" "$TARGET/.agents/skills")
fi

if [ "$STATUS" = 1 ]; then
  echo "This copy: powerbi-architect $VERSION ($SRC)"
  for d in "${DESTS[@]}"; do
    dest="$d/powerbi-architect"
    if [ -L "$dest" ]; then echo "  $dest: linked, always current"
    elif [ -e "$dest" ]; then
      v="$(version_of "$dest")"
      if [ "$v" = "$VERSION" ]; then echo "  $dest: $v (up to date)"; else echo "  $dest: $v (update available: $VERSION)"; fi
    else echo "  $dest: not installed"; fi
  done
  exit 0
fi

CHANGED=0
for d in "${DESTS[@]}"; do
  dest="$d/powerbi-architect"
  if [ "$UPDATE" = 1 ]; then
    if [ -L "$dest" ]; then echo "• linked, always current: $dest"; continue; fi
    if [ ! -e "$dest" ]; then echo "• not installed, skipped: $dest"; continue; fi
    old="$(version_of "$dest")"
    if [ "$old" = "$VERSION" ] && [ "$FORCE" = 0 ]; then echo "• up to date ($VERSION): $dest"; continue; fi
    rm -rf "$dest"
    echo "  $old -> $VERSION"
  elif [ -e "$dest" ] || [ -L "$dest" ]; then
    if [ "$FORCE" = 1 ]; then rm -rf "$dest"; else echo "• exists, skipped: $dest (use --force, or --update)"; continue; fi
  fi
  CHANGED=1
  mkdir -p "$d"
  if [ "$LINK" = 1 ]; then ln -s "$SRC" "$dest"; else
    cp -R "$SRC" "$dest"
    rm -rf "$dest/templates/pbiviz-bullet-kpi/node_modules" 2>/dev/null || true
  fi
  echo "[ok] $dest"
done
echo
if [ "$UPDATE" = 1 ] && [ "$CHANGED" = 0 ]; then echo "Nothing to update."; exit 0; fi
echo "powerbi-architect $VERSION installed."
if [ "$GLOBAL" = 0 ] && [ "$GRAPH" = 1 ]; then
  PY=""
  for c in python3 python; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c "import sys; sys.exit(sys.version_info < (3, 9))" 2>/dev/null; then PY="$c"; break; fi
  done
  if [ -z "$PY" ]; then
    echo "! Python 3.9+ not found — knowledge graph skipped. Later: python .claude/skills/powerbi-architect/scripts/pbi_graph.py install ."
  else
    echo
    echo "Building the Power BI knowledge graph…"
    EXTRA=(); [ "$HOOKS" = 0 ] && EXTRA+=(--no-hooks)
    (cd "$TARGET" && "$PY" ".claude/skills/powerbi-architect/scripts/pbi_graph.py" install . "${EXTRA[@]+"${EXTRA[@]}"}")
  fi
elif [ "$GLOBAL" = 1 ]; then
  echo "Global install: build a repository's graph with"
  echo "  python ~/.claude/skills/powerbi-architect/scripts/pbi_graph.py install /path/to/repo"
fi
echo
echo "Ask your AI: \"use the powerbi-architect skill to …\" — or just ask for Power BI work; it loads automatically."
