from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


class RuntimeService:
    def __init__(self, db: Session):
        self.db = db

    def database_status(self) -> dict[str, object]:
        bind = self.db.get_bind()
        dialect = bind.dialect.name
        database_url = bind.url
        persistent = not (dialect == "sqlite" and database_url.database in (None, "", ":memory:"))
        try:
            self.db.execute(text("SELECT 1"))
        except SQLAlchemyError:
            return {"status": "unavailable", "dialect": dialect, "persistent": persistent}
        return {"status": "connected", "dialect": dialect, "persistent": persistent}
