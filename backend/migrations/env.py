from alembic import context
from sqlalchemy import create_engine
from app.core.config import get_settings
from app.db.base import Base
from app.models import entities

engine = create_engine(get_settings().database_url)
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
