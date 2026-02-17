import sqlite3

DB_PATH = "hr.db"
COL_NAME = "pension_self_6"

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(employees)")
    cols = [r[1] for r in cur.fetchall()]

    if COL_NAME in cols:
        print(f"OK: column already exists: {COL_NAME}")
        conn.close()
        return

    cur.execute(f"ALTER TABLE employees ADD COLUMN {COL_NAME} INTEGER NOT NULL DEFAULT 0;")
    conn.commit()
    conn.close()
    print(f"OK: added column {COL_NAME} to employees")

if __name__ == "__main__":
    main()
