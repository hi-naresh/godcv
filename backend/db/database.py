import aiosqlite
import json
from pathlib import Path
from backend.config import DB_PATH

_db: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        _db = await aiosqlite.connect(DB_PATH)
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL")
        await _db.execute("PRAGMA foreign_keys=ON")
        await _init_tables(_db)
    return _db


async def close_db():
    global _db
    if _db:
        await _db.close()
        _db = None


async def _init_tables(db: aiosqlite.Connection):
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            master_resume TEXT NOT NULL,
            parsed_sections TEXT,
            gemini_api_key TEXT DEFAULT '',
            page_mode TEXT DEFAULT 'single',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS role_insights (
            id INTEGER PRIMARY KEY,
            profile_id INTEGER REFERENCES profiles(id) ON DELETE CASCADE,
            role_type TEXT NOT NULL,
            strongest_points TEXT DEFAULT '[]',
            preferred_skill_order TEXT DEFAULT '[]',
            frequently_modified_sections TEXT DEFAULT '[]',
            tailoring_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS tailoring_history (
            id INTEGER PRIMARY KEY,
            profile_id INTEGER REFERENCES profiles(id) ON DELETE CASCADE,
            job_title TEXT,
            company TEXT,
            job_description TEXT NOT NULL,
            original_resume TEXT NOT NULL,
            tailored_resume TEXT NOT NULL,
            orchestrator_plan TEXT,
            role_type TEXT,
            sections_modified TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    await db.commit()

    # Migrations for existing databases
    cursor = await db.execute("PRAGMA table_info(profiles)")
    columns = [row[1] for row in await cursor.fetchall()]
    if "page_mode" not in columns:
        await db.execute("ALTER TABLE profiles ADD COLUMN page_mode TEXT DEFAULT 'single'")
        await db.commit()
