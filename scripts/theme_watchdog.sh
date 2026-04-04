#!/usr/bin/env bash
set -euo pipefail

TODO_FILE="/home/oriol/.openclaw/workspace/aigor-app/docs/THEME_VISUAL_IMMUTABLE_TODO.md"
LOG_FILE="/home/oriol/.openclaw/workspace/aigor-app/docs/THEME_WATCHDOG.log"
WEB_FILE="/mnt/apps/web/themeStatus.html"
NOW_UTC="$(date -u '+%Y-%m-%d %H:%M UTC')"

mkdir -p "$(dirname "$LOG_FILE")"
mkdir -p "$(dirname "$WEB_FILE")"

if [[ ! -f "$TODO_FILE" ]]; then
  echo "[$NOW_UTC] ERROR: TODO file missing: $TODO_FILE" >> "$LOG_FILE"
  exit 1
fi

current_task="$(grep '^- CURRENT_TASK:' "$TODO_FILE" | sed 's/^- CURRENT_TASK: //')"
status="$(grep '^- STATUS:' "$TODO_FILE" | sed 's/^- STATUS: //')"
progress="$(grep '^- PROGRESS:' "$TODO_FILE" | sed 's/^- PROGRESS: //')"

if ! [[ "$current_task" =~ ^T[1-9]$ ]]; then
  echo "[$NOW_UTC] BLOCKER: CURRENT_TASK fora de T1→T9: $current_task" >> "$LOG_FILE"
  cat > "$WEB_FILE" <<HTML
<!doctype html><html><head><meta charset="utf-8"><title>Theme Status</title></head><body>
<h1>aigor-app theme watchdog</h1>
<p><strong>Últim update UTC:</strong> $NOW_UTC</p>
<p><strong>STATUS:</strong> BLOCKED</p>
<p><strong>BLOCKER:</strong> CURRENT_TASK fora de rang immutable: $current_task</p>
</body></html>
HTML
  exit 2
fi

next_line="$(grep -n '^- \[ \] T[1-9] ' "$TODO_FILE" | head -n 1 || true)"
if [[ -z "$next_line" ]]; then
  new_status="DONE"
  new_progress="9/9"
  sed -i "s/^- STATUS: .*/- STATUS: ${new_status}/" "$TODO_FILE"
  sed -i "s/^- PROGRESS: .*/- PROGRESS: ${new_progress}/" "$TODO_FILE"
  echo "[$NOW_UTC] DONE: cap tasca pendent; bloc immutable complet." >> "$LOG_FILE"
  cat > "$WEB_FILE" <<HTML
<!doctype html><html><head><meta charset="utf-8"><title>Theme Status</title></head><body>
<h1>aigor-app theme watchdog</h1>
<p><strong>Últim update UTC:</strong> $NOW_UTC</p>
<p><strong>STATUS:</strong> DONE</p>
<p><strong>PROGRESS:</strong> 9/9</p>
<p><strong>Acció:</strong> bloc immutable completat</p>
</body></html>
HTML
  exit 0
fi

line_no="${next_line%%:*}"
line_text="${next_line#*:}"
task_id="$(echo "$line_text" | sed -E 's/^- \[ \] (T[1-9]).*/\1/')"

echo "[$NOW_UTC] WATCHDOG: següent tasca prevista = $task_id" >> "$LOG_FILE"
sed -i "s/^- CURRENT_TASK: .*/- CURRENT_TASK: ${task_id}/" "$TODO_FILE"
sed -i "s/^- STATUS: .*/- STATUS: IN_PROGRESS/" "$TODO_FILE"

cat > "$WEB_FILE" <<HTML
<!doctype html><html><head><meta charset="utf-8"><title>Theme Status</title></head><body>
<h1>aigor-app theme watchdog</h1>
<p><strong>Últim update UTC:</strong> $NOW_UTC</p>
<p><strong>STATUS:</strong> IN_PROGRESS</p>
<p><strong>PROGRESS:</strong> $progress</p>
<p><strong>CURRENT_TASK:</strong> $task_id</p>
<p><strong>Next exact action:</strong> executar la següent tasca pendent del bloc immutable T1→T9, sense afegir-ne cap de nova.</p>
</body></html>
HTML
