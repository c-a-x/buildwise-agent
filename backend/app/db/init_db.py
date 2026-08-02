from app.db.base import Base
from app.db.session import engine
from app.models import *  # noqa: F401,F403


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
