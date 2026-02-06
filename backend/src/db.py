import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional


def _db_path() -> str:
    default_path = Path(__file__).resolve().parents[1] / "data" / "farmers.db"
    return str(default_path)


def _connect(db_path: Optional[str] = None) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path or _db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    conn = _connect(db_path)
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
    conn.commit()
    conn.close()


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


def list_farmers() -> list[dict]:
    conn = _connect()
    rows = conn.execute("SELECT * FROM farmers ORDER BY id").fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_farmer(farmer_id: str) -> Optional[dict]:
    conn = _connect()
    row = conn.execute("SELECT * FROM farmers WHERE id = ?", (farmer_id,)).fetchone()
    conn.close()
    return _row_to_dict(row) if row else None


def create_farmer(payload: dict) -> dict:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO farmers (
            id, name, name_en, phone, village, district, state,
            account_number, ifsc_code, bank_name, survey_number,
            area_acres, enrolled_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload.get("id"),
            payload.get("name"),
            payload.get("name_en"),
            payload.get("phone"),
            payload.get("village"),
            payload.get("district"),
            payload.get("state"),
            payload.get("account_number"),
            payload.get("ifsc_code"),
            payload.get("bank_name"),
            payload.get("survey_number"),
            payload.get("area_acres"),
            payload.get("enrolled_date"),
        ),
    )
    conn.commit()
    farmer = get_farmer(payload.get("id"))
    conn.close()
    return farmer


def update_farmer(farmer_id: str, updates: dict) -> Optional[dict]:
    if not updates:
        return get_farmer(farmer_id)
    fields = ", ".join([f"{k} = ?" for k in updates.keys()])
    values = list(updates.values()) + [farmer_id]
    conn = _connect()
    cur = conn.cursor()
    cur.execute(f"UPDATE farmers SET {fields} WHERE id = ?", values)
    conn.commit()
    farmer = get_farmer(farmer_id)
    conn.close()
    return farmer


def delete_farmer(farmer_id: str) -> bool:
    conn = _connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM farmers WHERE id = ?", (farmer_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


def get_profile(farmer_id: str) -> Optional[dict]:
    conn = _connect()
    row = conn.execute("SELECT * FROM profiles WHERE farmer_id = ?", (farmer_id,)).fetchone()
    conn.close()
    return _row_to_dict(row) if row else None


def upsert_profile(payload: dict) -> dict:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO profiles (farmer_id, full_name, phone, address, offline_enabled, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(farmer_id) DO UPDATE SET
            full_name = excluded.full_name,
            phone = excluded.phone,
            address = excluded.address,
            offline_enabled = excluded.offline_enabled,
            updated_at = excluded.updated_at
        """,
        (
            payload.get("farmer_id"),
            payload.get("full_name"),
            payload.get("phone"),
            payload.get("address"),
            1 if payload.get("offline_enabled") else 0,
            datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    profile = get_profile(payload.get("farmer_id"))
    conn.close()
    return profile


def delete_profile(farmer_id: str) -> bool:
    conn = _connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM profiles WHERE farmer_id = ?", (farmer_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


def list_documents(farmer_id: Optional[str] = None) -> list[dict]:
    conn = _connect()
    if farmer_id:
        rows = conn.execute(
            "SELECT * FROM documents WHERE farmer_id = ? ORDER BY id DESC",
            (farmer_id,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM documents ORDER BY id DESC").fetchall()
    conn.close()
    documents = []
    for row in rows:
        doc = _row_to_dict(row)
        if doc.get("metadata"):
            doc["metadata"] = json.loads(doc["metadata"])
        documents.append(doc)
    return documents


def get_document(doc_id: int) -> Optional[dict]:
    conn = _connect()
    row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    conn.close()
    if not row:
        return None
    doc = _row_to_dict(row)
    if doc.get("metadata"):
        doc["metadata"] = json.loads(doc["metadata"])
    return doc


def create_document(payload: dict) -> dict:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO documents (farmer_id, filename, status, metadata, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            payload.get("farmer_id"),
            payload.get("filename"),
            payload.get("status", "pending"),
            json.dumps(payload.get("metadata")) if payload.get("metadata") else None,
            datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    doc_id = cur.lastrowid
    conn.close()
    return get_document(doc_id)


def update_document(doc_id: int, updates: dict) -> Optional[dict]:
    if not updates:
        return get_document(doc_id)
    if "metadata" in updates and updates["metadata"] is not None:
        updates["metadata"] = json.dumps(updates["metadata"])
    fields = ", ".join([f"{k} = ?" for k in updates.keys()])
    values = list(updates.values()) + [doc_id]
    conn = _connect()
    cur = conn.cursor()
    cur.execute(f"UPDATE documents SET {fields} WHERE id = ?", values)
    conn.commit()
    doc = get_document(doc_id)
    conn.close()
    return doc


def delete_document(doc_id: int) -> bool:
    conn = _connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted
