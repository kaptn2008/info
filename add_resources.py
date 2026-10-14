
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "database" / "infodz.db"

resources = [
    (
        "ALGO",
        "شرح الخوارزميات للمبتدئين",
        "video",
        "ar",
        "https://www.youtube.com/results?search_query=شرح+الخوارزميات+للسنة+الأولى+جامعة",
        "ALL",
        "بحث عن دروس عربية في الخوارزميات"
    ),
    (
        "C",
        "Cours de programmation C",
        "course",
        "fr",
        "https://www.youtube.com/results?search_query=cours+programmation+C+débutant+université",
        "ALL",
        "Recherche de cours en français"
    ),
    (
        "ANALYSE",
        "Cours d'analyse mathématique L1",
        "course",
        "fr",
        "https://www.youtube.com/results?search_query=analyse+mathématique+L1+université",
        "ALL",
        "Recherche de cours universitaires"
    ),
]

with sqlite3.connect(DB_PATH) as conn:
    for code, title, kind, lang, url, university, description in resources:
        subject = conn.execute(
            "SELECT id FROM subjects WHERE code = ?",
            (code,)
        ).fetchone()

        if subject:
            conn.execute("""
                INSERT INTO resources
                (subject_id, title, resource_type, language, url,
                 university_code, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                subject[0], title, kind, lang, url,
                university, description
            ))

print("Sample resources added.")
