import json
import sqlite3
from pathlib import Path

root = Path(__file__).resolve().parents[2]
db_path = root / "backend" / "data" / "farmers.db"
json_path = root / "backend" / "data" / "farmers.json"

db_path.parent.mkdir(parents=True, exist_ok=True)

with json_path.open("r", encoding="utf-8") as f:
    farmers = json.load(f)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute(
    """
    CREATE TABLE IF NOT EXISTS farmers (
        id TEXT PRIMARY KEY,
        name TEXT,
        name_en TEXT,
        phone TEXT,
        village TEXT,
        district TEXT,
        state TEXT,
        account_number TEXT,
        ifsc_code TEXT,
        bank_name TEXT,
        survey_number TEXT,
        area_acres REAL,
        enrolled_date TEXT
    )
    """
)

cur.execute(
    """
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        farmer_id TEXT,
        filename TEXT,
        status TEXT,
        metadata TEXT,
        created_at TEXT,
        FOREIGN KEY (farmer_id) REFERENCES farmers(id)
    )
    """
)

cur.execute(
    """
    CREATE TABLE IF NOT EXISTS profiles (
        farmer_id TEXT PRIMARY KEY,
        full_name TEXT,
        phone TEXT,
        address TEXT,
        offline_enabled INTEGER DEFAULT 0,
        updated_at TEXT,
        FOREIGN KEY (farmer_id) REFERENCES farmers(id)
    )
    """
)

cur.execute("DELETE FROM farmers")
cur.executemany(
    """
    INSERT INTO farmers (
        id, name, name_en, phone, village, district, state,
        account_number, ifsc_code, bank_name, survey_number,
        area_acres, enrolled_date
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
    [
        (
            f.get("id"),
            f.get("name"),
            f.get("name_en"),
            f.get("phone"),
            f.get("village"),
            f.get("district"),
            f.get("state"),
            f.get("account_number"),
            f.get("ifsc_code"),
            f.get("bank_name"),
            f.get("survey_number"),
            f.get("area_acres"),
            f.get("enrolled_date"),
        )
        for f in farmers
    ],
)

conn.commit()
conn.close()

print(f"SQLite DB created at: {db_path}")
