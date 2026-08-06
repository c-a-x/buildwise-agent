from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import KnowledgeDocument, Project, ProjectMember, User
from app.utils.ids import new_id


DEMO_PASSWORD = "BuildWise123!"


def _ingest_knowledge(db, json_path: Path) -> int:
    """把单个规范 JSON 文件按稳定 ID 增量灌入 KnowledgeDocument。返回导入条数。"""
    documents: list[dict[str, object]] = []
    if json_path.exists():
        try:
            parsed = json.loads(json_path.read_text(encoding="utf-8"))
            if isinstance(parsed, list):
                documents = [item for item in parsed if isinstance(item, dict)]
        except (OSError, json.JSONDecodeError):
            documents = []
    for item in documents:
        document_id = str(item.get("id", new_id("KNO")))
        if not db.get(KnowledgeDocument, document_id):
            metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
            metadata = {**metadata, "hazard_types": item.get("hazard_types", metadata.get("hazard_types", [])), "keywords": item.get("keywords", metadata.get("keywords", [])), "document_id": document_id}
            db.add(KnowledgeDocument(id=document_id, title=str(item.get("title", item.get("article", "条款"))), source=str(item.get("source", "项目管理制度")), version=str(item.get("version", "MVP")), article=str(item.get("article", "")), category=str(item.get("category", "施工管理")), effective_date=str(item.get("effective_date")) if item.get("effective_date") else None, content=str(item.get("content", "")), metadata_json=metadata, status="active"))
    return len(documents)


def seed_database() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        users = [
            ("USR-000", "admin", "演示管理员", "admin"),
            ("USR-001", "manager", "演示项目经理", "project_manager"),
            ("USR-002", "safety", "演示安全员", "safety_officer"),
            ("USR-003", "quality", "演示质检员", "quality_inspector"),
            ("USR-004", "worker", "演示工友", "worker"),
        ]
        by_username: dict[str, User] = {}
        for user_id, username, real_name, role in users:
            user = db.get(User, user_id) or db.query(User).filter(User.username == username).first()
            if not user:
                user = User(id=user_id, username=username, real_name=real_name, role=role, password_hash=hash_password(DEMO_PASSWORD), is_active=True)
                db.add(user)
            else:
                user.password_hash = hash_password(DEMO_PASSWORD)
                user.real_name = real_name
                user.role = role
            by_username[username] = user
        db.flush()
        project = db.get(Project, "PRJ-001") or db.query(Project).filter(Project.code == "DEMO-001").first()
        if not project:
            project = Project(id="PRJ-001", code="DEMO-001", name="滨江智造中心一期", address="上海市浦东新区滨江大道 88 号", description="BuildWise 演示项目：用于安全闭环、工单和日报演示。", status="active", manager_user_id=by_username["manager"].id)
            db.add(project)
        else:
            project.manager_user_id = by_username["manager"].id
        db.flush()
        for username, project_role in (("manager", "manager"), ("safety", "safety"), ("quality", "quality"), ("worker", "worker")):
            user = by_username[username]
            if not db.query(ProjectMember).filter(ProjectMember.project_id == project.id, ProjectMember.user_id == user.id).first():
                db.add(ProjectMember(id=new_id("MEM"), project_id=project.id, user_id=user.id, project_role=project_role))
        # 中国建筑公开披露的代表性真实项目（增强演示真实感）。created_at 回填到竣工/封顶年份，
        # 保证项目列表按 created_at desc 排序后 PRJ-001 仍是默认当前项目，不影响演示主流程。
        manager = by_username["manager"]
        real_projects = [
            ("PRJ-002", "REAL-002", "北京中信大厦（中国尊）", "北京市朝阳区光华路 CBD", "中国建筑承建代表作：总高 528 米、总建筑面积约 43.7 万平方米，中信集团总部大楼，中建股份—中建三局联合体施工总承包，2018 年移交。来源：公开项目资料。", 2018),
            ("PRJ-003", "REAL-003", "深圳平安金融中心", "深圳市福田区", "中建一局（中国建筑旗下）施工总承包：最终高度 599.1 米，2016 年全面竣工。来源：公开项目资料。", 2016),
            ("PRJ-004", "REAL-004", "广州周大福金融中心（广州东塔）", "广州市天河区珠江新城", "中国建筑股份有限公司施工总承包（中建三局、中建四局联合承建）：总高 530 米，2014 年封顶。来源：公开项目资料。", 2014),
        ]
        for project_id, code, name, address, description, completed_year in real_projects:
            real = db.get(Project, project_id)
            if not real:
                real = Project(id=project_id, code=code, name=name, address=address, description=description, status="active", manager_user_id=manager.id, created_at=datetime(completed_year, 1, 1, tzinfo=timezone.utc))
                db.add(real)
            else:
                real.manager_user_id = manager.id
            db.flush()
            for username, project_role in (("manager", "manager"), ("safety", "safety"), ("quality", "quality"), ("worker", "worker")):
                user = by_username[username]
                if not db.query(ProjectMember).filter(ProjectMember.project_id == real.id, ProjectMember.user_id == user.id).first():
                    db.add(ProjectMember(id=new_id("MEM"), project_id=real.id, user_id=user.id, project_role=project_role))
        safety_docs = _ingest_knowledge(db, settings.knowledge_json_path)
        quality_docs = _ingest_knowledge(db, settings.quality_knowledge_json_path)
        db.commit()
        print(f"Seed complete: {len(users)} users, project={project.code}, knowledge=safety:{safety_docs} quality:{quality_docs}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
