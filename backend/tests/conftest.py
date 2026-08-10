from __future__ import annotations

import os

# 测试固定使用离线 mock 视觉，与开发者本地 .env 解耦（本地可能设为 safety_hybrid）
os.environ.setdefault("VISION_PROVIDER", "mock")
os.environ.setdefault("VISION_LLM_PROVIDER", "off")
# 文本生成同样固定离线（本地可能设为 openai_compatible/DeepSeek，测试不应发起外部 LLM 请求）
os.environ.setdefault("TEXT_PROVIDER", "template")
# 关闭定时关怀调度，避免 TestClient 触发 lifespan 时在测试内启动后台调度器
os.environ.setdefault("CARE_SCHEDULE_ENABLED", "false")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import KnowledgeDocument, Project, ProjectMember, User


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    db = session_factory()
    users = [
        User(id="USR-001", username="manager", real_name="演示项目经理", role="project_manager", password_hash=hash_password("BuildWise123!"), is_active=True),
        User(id="USR-002", username="safety", real_name="演示安全员", role="safety_officer", password_hash=hash_password("BuildWise123!"), is_active=True),
        User(id="USR-003", username="quality", real_name="演示质检员", role="quality_inspector", password_hash=hash_password("BuildWise123!"), is_active=True),
        User(id="USR-004", username="worker", real_name="演示工友", role="worker", password_hash=hash_password("BuildWise123!"), is_active=True),
    ]
    db.add_all(users)
    db.add(Project(id="PRJ-001", code="DEMO-001", name="测试演示项目", address="测试地址", description="", status="active", manager_user_id="USR-001"))
    db.flush()
    db.add_all([ProjectMember(project_id="PRJ-001", user_id=user.id, project_role=user.role) for user in users])
    db.add(KnowledgeDocument(id="STD-HELMET-001", title="施工现场佩戴安全帽", source="项目制度", version="MVP", category="个人防护", content="进入施工现场的人员应正确佩戴安全帽。", metadata_json={"hazard_types": ["no_helmet"], "keywords": ["安全帽"]}, status="active"))
    db.commit()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def client(db_session: Session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def login(client: TestClient, username: str = "safety") -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": "BuildWise123!"})
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
