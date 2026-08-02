from sqlalchemy.orm import Session

from app.models import KnowledgeDocument


class KnowledgeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self) -> list[KnowledgeDocument]:
        return self.db.query(KnowledgeDocument).order_by(KnowledgeDocument.category, KnowledgeDocument.title).all()
