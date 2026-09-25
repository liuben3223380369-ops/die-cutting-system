#!/bin/bash
# 简易 SQLite 备份
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DB="$ROOT/data/die_cutting.db"
BACKUP_DIR="$ROOT/data/backups"
mkdir -p "$BACKUP_DIR"
TS=$(date +%Y%m%d_%H%M%S)
if [ -f "$DB" ]; then
  cp "$DB" "$BACKUP_DIR/die_cutting_$TS.db"
  echo "Backup OK: $BACKUP_DIR/die_cutting_$TS.db"
else
  echo "DB not found: $DB"
  exit 1
fi
