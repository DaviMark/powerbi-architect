#!/usr/bin/env bash
# Install the powerbi-architect skill into a repository (or globally) for every major AI agent.
#
#   ./install/install.sh [TARGET_REPO] [--global] [--link] [--force] [--no-graph] [--no-hooks]
#
#   TARGET_REPO  repository to install into (default: current directory)
#   --global     install in your user folders instead (~/.claude, ~/.copilot, ~/.codex)
#   --link       symlink instead of copy (updates with `git pull` in this repo)
#   --force      replace an existing installation
#   --no-graph   only copy files: do not build the Power BI knowledge graph
#   --no-hooks   build the graph but do not add auto-refresh hooks (Claude Code, git)
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
TARGET="."; GLOBAL=0; LINK=0; FORCE=0; GRAPH=1; HOOKS=1
for arg in "$@"; do
  case "$arg" in
    --global) GLOBAL=1 ;;
    --link)   LINK=1 ;;
    --force)  FORCE=1 ;;
    --no-graph) GRAPH=0 ;;
    --no-hooks) HOOKS=0 ;;
    -h|--help) sed -n '2,19p' "$0"; exit 0 ;;
    *) TARGET="$arg" ;;
  esac
done
[ -f "$SRC/SKILL.md" ] || { echo "SKILL.md not found in $SRC" >&2; exit 1; }

if [ "$GLOBAL" = 1 ]; then
  DESTS=("$HOME/.claude/skills" "$HOME/.copilot/skills" "$HOME/.codex/skills")
else
  [ -d "$TARGET" ] || { echo "Target folder not found: $TARGET" >&2; exit 1; }
  TARGET="$(cd "$TARGET" && pwd)"
  DESTS=("$TARGET/.claude/skills" "$TARGET/.github/skills" "$TARGET/.agents/skills")
fi

for d in "${DESTS[@]}"; do
  dest="$d/powerbi-architect"
  if [ -e "$dest" ] || [ -L "$dest" ]; then
    if [ "$FORCE" = 1 ]; then rm -rf "$dest"; else echo "• exists, skipped: $dest (use --force)"; continue; fi
  fi
  mkdir -p "$d"
  if [ "$LINK" = 1 ]; then ln -s "$SRC" "$dest"; else
    cp -R "$SRC" "$dest"
    rm -rf "$dest/templates/pbiviz-bullet-kpi/node_modules" 2>/dev/null || true
  fi
  echo "✔ $dest"
done
echo
echo "powerbi-architect $(grep -m1 'version:' "$SRC/SKILL.md" | tr -d ' "' | cut -d: -f2) installed."
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
