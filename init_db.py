
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "database" / "infodz.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

with sqlite3.connect(DB_PATH) as conn:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS universities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name_ar TEXT NOT NULL,
            name_fr TEXT NOT NULL,
            code TEXT UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name_ar TEXT NOT NULL,
            name_fr TEXT NOT NULL,
            code TEXT UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            language TEXT NOT NULL,
            url TEXT NOT NULL,
            university_code TEXT DEFAULT 'ALL',
            description TEXT DEFAULT '',
            FOREIGN KEY (subject_id) REFERENCES subjects(id)
        );

        CREATE INDEX IF NOT EXISTS idx_resource_subject
        ON resources(subject_id);

        CREATE INDEX IF NOT EXISTS idx_resource_type
        ON resources(resource_type);
    """)

    conn.execute("""
        INSERT OR IGNORE INTO universities
        (name_ar, name_fr, code)
        VALUES (?, ?, ?)
    """, (
        "جامعة 20 أوت 1955 سكيكدة",
        "Université 20 Août 1955 Skikda",
        "SKIKDA"
    ))

    subjects = [
        ("الخوارزميات", "Algorithmique", "ALGO"),
        ("البرمجة بلغة C", "Programmation C", "C"),
        ("التحليل الرياضي", "Analyse", "ANALYSE"),
        ("الجبر", "Algèbre", "ALGEBRE"),
        ("بنية الحاسوب", "Architecture des ordinateurs", "ARCHI"),
        ("المنطق الرياضي", "Logique", "LOGIQUE"),
        ("أنظمة التشغيل", "Systèmes d'exploitation", "OS"),
    ]

    conn.executemany("""
        INSERT OR IGNORE INTO subjects
        (name_ar, name_fr, code)
        VALUES (?, ?, ?)
    """, subjects)

print(f"Database initialized: {DB_PATH}")
