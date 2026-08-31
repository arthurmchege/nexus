from sqlalchemy import text

from app.db.session import engine


def create_db_and_tables() -> None:
    with engine.begin() as connection:
        connection.execute(text("SELECT 1"))
