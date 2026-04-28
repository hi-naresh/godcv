import pytest
import pytest_asyncio
from backend.db import database
from backend.services import profile as profile_service


@pytest_asyncio.fixture(autouse=True)
async def isolated_db(tmp_path, monkeypatch):
    # Point DB_PATH at a fresh per-test sqlite file and reset module-level connection.
    # `database.py` does `from backend.config import DB_PATH`, so we must patch the
    # name re-bound inside the database module, not the source in backend.config.
    db_file = tmp_path / "test.db"
    monkeypatch.setattr(database, "DB_PATH", str(db_file))
    monkeypatch.setattr(database, "_db", None)
    yield
    if database._db is not None:
        await database._db.close()
        database._db = None


@pytest.mark.asyncio
async def test_create_profile_defaults_fabrication_off():
    p = await profile_service.create_profile(name="N", master_resume="m")
    assert p["fabrication_mode"] == 0


@pytest.mark.asyncio
async def test_create_profile_with_fabrication_on():
    p = await profile_service.create_profile(name="N", master_resume="m", fabrication_mode=True)
    assert p["fabrication_mode"] == 1


@pytest.mark.asyncio
async def test_update_profile_toggles_fabrication():
    p = await profile_service.create_profile(name="N", master_resume="m")
    updated = await profile_service.update_profile(p["id"], fabrication_mode=True)
    assert updated["fabrication_mode"] == 1
    updated = await profile_service.update_profile(p["id"], fabrication_mode=False)
    assert updated["fabrication_mode"] == 0
