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
            stealth_mode INTEGER DEFAULT 0,
            max_projects INTEGER DEFAULT 4,
            max_bullets_per_entry INTEGER DEFAULT 3,
            require_quantified_bullets INTEGER DEFAULT 1,
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

        CREATE TABLE IF NOT EXISTS saved_cvs (
            id INTEGER PRIMARY KEY,
            profile_id INTEGER REFERENCES profiles(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            markdown TEXT NOT NULL,
            job_title TEXT,
            company TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

        CREATE TABLE IF NOT EXISTS job_retry_budgets (
            job_class TEXT PRIMARY KEY,
            max_retries INTEGER NOT NULL DEFAULT 5,
            base_delay_seconds INTEGER NOT NULL DEFAULT 30,
            max_delay_seconds INTEGER NOT NULL DEFAULT 1800,
            backoff_multiplier REAL NOT NULL DEFAULT 2.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS job_queue (
            id INTEGER PRIMARY KEY,
            job_class TEXT NOT NULL,
            payload TEXT NOT NULL DEFAULT '{}',
            idempotency_key TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'queued',
            attempt_count INTEGER NOT NULL DEFAULT 0,
            run_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            result TEXT,
            last_error TEXT,
            quarantine_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            finished_at TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_job_queue_status_run_at ON job_queue(status, run_at);
        CREATE INDEX IF NOT EXISTS idx_job_queue_class_status ON job_queue(job_class, status);

        CREATE TABLE IF NOT EXISTS job_failure_events (
            id INTEGER PRIMARY KEY,
            job_id INTEGER NOT NULL REFERENCES job_queue(id) ON DELETE CASCADE,
            attempt_number INTEGER NOT NULL,
            error_message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_job_failure_events_job_id ON job_failure_events(job_id);
    """)
    await db.commit()

    # Migrations for existing databases
    cursor = await db.execute("PRAGMA table_info(profiles)")
    columns = [row[1] for row in await cursor.fetchall()]
    if "page_mode" not in columns:
        await db.execute("ALTER TABLE profiles ADD COLUMN page_mode TEXT DEFAULT 'single'")
        await db.commit()
    # Rename fabrication_mode → stealth_mode (idempotent)
    if "fabrication_mode" in columns and "stealth_mode" not in columns:
        await db.execute("ALTER TABLE profiles RENAME COLUMN fabrication_mode TO stealth_mode")
        await db.commit()
    elif "stealth_mode" not in columns:
        # Fresh DB path didn't run for some reason — add the column
        await db.execute("ALTER TABLE profiles ADD COLUMN stealth_mode INTEGER DEFAULT 0")
        await db.commit()
    if "max_projects" not in columns:
        await db.execute("ALTER TABLE profiles ADD COLUMN max_projects INTEGER DEFAULT 4")
        await db.commit()
    if "max_bullets_per_entry" not in columns:
        await db.execute("ALTER TABLE profiles ADD COLUMN max_bullets_per_entry INTEGER DEFAULT 3")
        await db.commit()
    if "require_quantified_bullets" not in columns:
        await db.execute("ALTER TABLE profiles ADD COLUMN require_quantified_bullets INTEGER DEFAULT 1")
        await db.commit()

    cursor = await db.execute("PRAGMA table_info(job_queue)")
    job_queue_columns = [row[1] for row in await cursor.fetchall()]
    if job_queue_columns and "result" not in job_queue_columns:
        await db.execute("ALTER TABLE job_queue ADD COLUMN result TEXT")
        await db.commit()
