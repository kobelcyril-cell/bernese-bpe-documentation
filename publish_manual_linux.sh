#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

command -v git >/dev/null 2>&1 || { echo "Fehler: git ist nicht installiert."; exit 2; }

echo "Dieses Skript pusht das bereits gebaute site/-Verzeichnis nach GitHub."
[[ -f "$SCRIPT_DIR/site/index.html" ]] || {
  echo "Fehler: site/index.html fehlt. Zuerst das Manual mit update_manual.py erstellen."
  exit 2
}

if [[ ! -d .git ]]; then
  echo "Kein lokales Git-Repository gefunden."
  read -r -p "GitHub-Repository-URL: " REMOTE_URL
  [[ -n "$REMOTE_URL" ]] || { echo "Keine URL angegeben."; exit 2; }
  git init -b main 2>/dev/null || { git init; git branch -M main; }
  git remote add origin "$REMOTE_URL"
fi

if ! git remote get-url origin >/dev/null 2>&1; then
  read -r -p "GitHub-Repository-URL für origin: " REMOTE_URL
  [[ -n "$REMOTE_URL" ]] || { echo "Keine URL angegeben."; exit 2; }
  git remote add origin "$REMOTE_URL"
fi

git add -A
if ! git diff --cached --quiet; then
  git commit -m "Build and publish manual"
else
  echo "Keine neuen Änderungen. Der aktuelle Stand wird trotzdem gepusht."
fi
git push -u origin HEAD:main
echo "Upload erfolgreich. GitHub Actions veröffentlicht site/."
