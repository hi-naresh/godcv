import json
from backend.db.database import get_db
from backend.services.parser import parse_resume


async def get_profile(profile_id: int = 1) -> dict | None:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,))
    row = await cursor.fetchone()
    if not row:
        return None
    return dict(row)


async def create_profile(
    name: str, master_resume: str, gemini_api_key: str = "", page_mode: str = "single",
    fabrication_mode: bool = False, max_projects: int = 4,
    max_bullets_per_entry: int = 3, require_quantified_bullets: bool = True,
) -> dict:
    db = await get_db()
    parsed = parse_resume(master_resume)
    parsed_json = json.dumps({
        "sections": {k: v if not isinstance(v, dict) else v.get("_full", str(v))
                     for k, v in parsed["sections"].items()},
        "separators": parsed["separators"],
    })
    cursor = await db.execute(
        "INSERT INTO profiles (name, master_resume, parsed_sections, gemini_api_key, page_mode, fabrication_mode, max_projects, max_bullets_per_entry, require_quantified_bullets) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (name, master_resume, parsed_json, gemini_api_key, page_mode, int(bool(fabrication_mode)), max_projects, max_bullets_per_entry, int(bool(require_quantified_bullets))),
    )
    await db.commit()
    return await get_profile(cursor.lastrowid)


async def update_profile(profile_id: int, **kwargs) -> dict | None:
    db = await get_db()
    fields = []
    values = []
    BOOL_KEYS = ("fabrication_mode", "require_quantified_bullets")
    for key in ("name", "master_resume", "gemini_api_key", "page_mode", "fabrication_mode",
                "max_projects", "max_bullets_per_entry", "require_quantified_bullets"):
        if key in kwargs and kwargs[key] is not None:
            fields.append(f"{key} = ?")
            # Coerce bool → int for sqlite storage
            value = int(bool(kwargs[key])) if key in BOOL_KEYS else kwargs[key]
            values.append(value)

    if "master_resume" in kwargs and kwargs["master_resume"]:
        parsed = parse_resume(kwargs["master_resume"])
        parsed_json = json.dumps({
            "sections": {k: v if not isinstance(v, dict) else v.get("_full", str(v))
                         for k, v in parsed["sections"].items()},
            "separators": parsed["separators"],
        })
        fields.append("parsed_sections = ?")
        values.append(parsed_json)

    fields.append("updated_at = CURRENT_TIMESTAMP")
    values.append(profile_id)

    await db.execute(f"UPDATE profiles SET {', '.join(fields)} WHERE id = ?", values)
    await db.commit()
    return await get_profile(profile_id)


async def get_role_insights(profile_id: int) -> list[dict]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM role_insights WHERE profile_id = ? ORDER BY tailoring_count DESC",
        (profile_id,),
    )
    rows = await cursor.fetchall()
    results = []
    for row in rows:
        d = dict(row)
        for field in ("strongest_points", "preferred_skill_order", "frequently_modified_sections"):
            d[field] = json.loads(d[field]) if d[field] else []
        results.append(d)
    return results


async def upsert_role_insight(profile_id: int, role_type: str, strongest_points: list[str],
                               preferred_skill_order: list[str], modified_sections: list[str]):
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM role_insights WHERE profile_id = ? AND role_type = ?",
        (profile_id, role_type),
    )
    existing = await cursor.fetchone()

    if existing:
        existing = dict(existing)
        old_points = json.loads(existing["strongest_points"]) if existing["strongest_points"] else []
        merged_points = list(dict.fromkeys(strongest_points + old_points))[:10]
        old_skills = json.loads(existing["preferred_skill_order"]) if existing["preferred_skill_order"] else []
        merged_skills = list(dict.fromkeys(preferred_skill_order + old_skills))[:20]
        old_sections = json.loads(existing["frequently_modified_sections"]) if existing["frequently_modified_sections"] else []
        merged_sections = list(dict.fromkeys(modified_sections + old_sections))

        await db.execute(
            """UPDATE role_insights SET
               strongest_points = ?, preferred_skill_order = ?,
               frequently_modified_sections = ?, tailoring_count = tailoring_count + 1,
               updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (json.dumps(merged_points), json.dumps(merged_skills),
             json.dumps(merged_sections), existing["id"]),
        )
    else:
        await db.execute(
            """INSERT INTO role_insights
               (profile_id, role_type, strongest_points, preferred_skill_order,
                frequently_modified_sections, tailoring_count)
               VALUES (?, ?, ?, ?, ?, 1)""",
            (profile_id, role_type, json.dumps(strongest_points),
             json.dumps(preferred_skill_order), json.dumps(modified_sections)),
        )
    await db.commit()


async def delete_role_insight(insight_id: int):
    db = await get_db()
    await db.execute("DELETE FROM role_insights WHERE id = ?", (insight_id,))
    await db.commit()


async def save_tailoring(profile_id: int, job_title: str | None, company: str | None,
                          job_description: str, original_resume: str, tailored_resume: str,
                          orchestrator_plan: dict, role_type: str | None,
                          sections_modified: list[str]) -> int:
    db = await get_db()
    cursor = await db.execute(
        """INSERT INTO tailoring_history
           (profile_id, job_title, company, job_description, original_resume,
            tailored_resume, orchestrator_plan, role_type, sections_modified)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (profile_id, job_title, company, job_description, original_resume,
         tailored_resume, json.dumps(orchestrator_plan), role_type,
         json.dumps(sections_modified)),
    )
    await db.commit()
    return cursor.lastrowid


async def get_tailoring_history(profile_id: int, limit: int = 20) -> list[dict]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM tailoring_history WHERE profile_id = ? ORDER BY created_at DESC LIMIT ?",
        (profile_id, limit),
    )
    rows = await cursor.fetchall()
    results = []
    for row in rows:
        d = dict(row)
        d["sections_modified"] = json.loads(d["sections_modified"]) if d["sections_modified"] else []
        results.append(d)
    return results


async def get_tailoring_by_id(tailoring_id: int) -> dict | None:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM tailoring_history WHERE id = ?", (tailoring_id,))
    row = await cursor.fetchone()
    if not row:
        return None
    d = dict(row)
    d["sections_modified"] = json.loads(d["sections_modified"]) if d["sections_modified"] else []
    return d


async def delete_tailoring(tailoring_id: int):
    db = await get_db()
    await db.execute("DELETE FROM tailoring_history WHERE id = ?", (tailoring_id,))
    await db.commit()
