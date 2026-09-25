#!/usr/bin/env python3
"""库存守恒校验：余额应等于流水汇总（简化版，同步 sqlite）"""
import sqlite3
import sys
from pathlib import Path

db_path = Path(__file__).resolve().parent.parent / "data" / "die_cutting.db"
if not db_path.exists():
    print("DB not found:", db_path)
    sys.exit(1)

conn = sqlite3.connect(str(db_path))
cur = conn.cursor()

# 检查表是否存在
tables = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")}
if "stock_balances" not in tables or "stock_ledgers" not in tables:
    print("stock tables missing")
    sys.exit(1)

# 按 material+warehouse+batch+roll 汇总流水
ledger = {}
for row in cur.execute(
    "SELECT material_id, warehouse_id, IFNULL(location_id,-1), batch_no, roll_no, SUM(qty) "
    "FROM stock_ledgers GROUP BY 1,2,3,4,5"
):
    ledger[row[:5]] = row[5]

mismatches = []
for row in cur.execute(
    "SELECT material_id, warehouse_id, IFNULL(location_id,-1), batch_no, roll_no, qty FROM stock_balances"
):
    key = row[:5]
    bal = row[5] or 0
    led = ledger.get(key, 0) or 0
    if abs(float(bal) - float(led)) > 1e-6:
        mismatches.append((key, bal, led))

if mismatches:
    print(f"INCONSISTENT: {len(mismatches)} balance rows != ledger sum")
    for m in mismatches[:20]:
        print(" ", m)
    sys.exit(2)

print("OK: stock balances consistent with ledger sums")
conn.close()
