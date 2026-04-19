from backend.db.database import get_db


async def list_saved_cvs(profile_id: int, limit: int = 50) -> list[dict]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM saved_cvs WHERE profile_id = ? ORDER BY created_at DESC LIMIT ?",
        (profile_id, limit),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_saved_cv(cv_id: int) -> dict | None:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM saved_cvs WHERE id = ?", (cv_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def save_cv(profile_id: int, name: str, markdown: str, job_title: str | None = None, company: str | None = None) -> dict:
    db = await get_db()
    cursor = await db.execute(
        "INSERT INTO saved_cvs (profile_id, name, markdown, job_title, company) VALUES (?, ?, ?, ?, ?)",
        (profile_id, name, markdown, job_title, company),
    )
    await db.commit()
    return await get_saved_cv(cursor.lastrowid)


async def delete_saved_cv(cv_id: int):
    db = await get_db()
    await db.execute("DELETE FROM saved_cvs WHERE id = ?", (cv_id,))
    await db.commit()
