from pathlib import Path
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from app.core.config import get_settings


def test_upgrade_and_downgrade(tmp_path, monkeypatch):
    url = "sqlite:///" + (tmp_path / "migrations.db").as_posix()
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    root = Path(__file__).parents[2]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    try:
        command.upgrade(config, "head")
        engine = create_engine(url)
        with engine.connect() as connection:
            assert {"uploaded_files", "features", "measurements", "processing_events"} <= set(inspect(connection).get_table_names())
        engine.dispose()
        command.downgrade(config, "base")
        engine = create_engine(url)
        with engine.connect() as connection:
            assert "uploaded_files" not in inspect(connection).get_table_names()
        engine.dispose()
    finally:
        get_settings.cache_clear()
