"""One-off: list latest import insurance_brackets insured_salary_level (read-only)."""
import sqlite3
import os

base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(base, "hr.db")
conn = sqlite3.connect(db_path)

row = conn.execute(
    "SELECT id FROM insurance_bracket_imports ORDER BY id DESC LIMIT 1"
).fetchone()
if not row:
    print("No imports in DB")
else:
    imp_id = row[0]
    levels = conn.execute(
        "SELECT insured_salary_level FROM insurance_brackets WHERE import_id = ? ORDER BY insured_salary_level",
        (imp_id,),
    ).fetchall()
    levels = [x[0] for x in levels]
    print("Latest import_id:", imp_id)
    print("Total levels:", len(levels))
    print("First 15:", levels[:15])
    around_7500 = [x for x in levels if 7400 <= x <= 12000]
    print("Around 7500 (7400~12000):", around_7500)
    print("All levels:", levels)

conn.close()
