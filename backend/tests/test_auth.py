import inspect

import pytest

from app.api.v1.endpoints import users as users_endpoint
from app.api.v1.endpoints import auth as auth_endpoint
from app.core.security import verify_password
from app.models import AuditLog, User
from app.services import auth_service

from tests.conftest import login


def test_register_and_login(client):
    register = client.post("/api/v1/auth/register", json={"username": "new_safety", "real_name": "新安全员", "password": "Password123!", "password_confirm": "Password123!", "role": "safety_officer"})
    assert register.status_code == 200
    duplicate = client.post("/api/v1/auth/register", json={"username": "new_safety", "real_name": "新安全员", "password": "Password123!", "password_confirm": "Password123!", "role": "safety_officer"})
    assert duplicate.status_code == 409
    login = client.post("/api/v1/auth/login", json={"username": "new_safety", "password": "Password123!"})
    assert login.status_code == 200
    assert login.json()["data"]["user"]["role"] == "safety_officer"


def test_invalid_password(client):
    response = client.post("/api/v1/auth/login", json={"username": "safety", "password": "wrong-password"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"


def test_user_endpoints_delegate_profile_transactions_to_auth_service():
    source = inspect.getsource(users_endpoint)

    assert "record_audit" not in source
    assert ".commit(" not in source
    assert ".rollback(" not in source
    assert "client_ip(http_request)" in source


def test_refresh_is_audited_without_recording_the_token(client, db_session):
    headers = login(client, "safety")
    before = db_session.query(AuditLog).filter(AuditLog.action == "token_refresh").count()

    response = client.post("/api/v1/auth/refresh", headers=headers)

    assert response.status_code == 200
    assert response.json()["data"]["access_token"]
    row = db_session.query(AuditLog).filter(AuditLog.action == "token_refresh").one()
    assert before == 0
    assert row.user_id == "USR-002"
    assert row.resource_type == "auth"
    assert row.detail_json == {}


def test_refresh_endpoint_delegates_transaction_and_audit_to_auth_service():
    source = inspect.getsource(auth_endpoint.refresh)

    assert "record_audit" not in source
    assert ".commit(" not in source
    assert ".rollback(" not in source


def test_refresh_rolls_back_when_token_generation_fails(client, db_session, monkeypatch):
    headers = login(client, "safety")

    def fail_token(*args, **kwargs):
        raise RuntimeError("token generation unavailable")

    monkeypatch.setattr(auth_service, "create_access_token", fail_token)
    with pytest.raises(RuntimeError, match="token generation unavailable"):
        client.post("/api/v1/auth/refresh", headers=headers)

    assert db_session.query(AuditLog).filter(AuditLog.action == "token_refresh").count() == 0


def test_profile_update_rolls_back_when_audit_write_fails(client, db_session, monkeypatch):
    headers = login(client, "safety")

    def fail_audit(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(auth_service, "record_audit", fail_audit, raising=False)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        client.patch("/api/v1/users/me", headers=headers, json={"real_name": "不应落库", "phone": "13900000000"})

    db_session.expire_all()
    user = db_session.get(User, "USR-002")
    assert user is not None
    assert user.real_name == "演示安全员"
    assert user.phone is None


def test_password_change_rolls_back_when_audit_write_fails(client, db_session, monkeypatch):
    headers = login(client, "safety")

    def fail_audit(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(auth_service, "record_audit", fail_audit, raising=False)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        client.post(
            "/api/v1/users/me/password",
            headers=headers,
            json={"current_password": "BuildWise123!", "new_password": "ShouldNotPersist123!", "new_password_confirm": "ShouldNotPersist123!"},
        )

    db_session.expire_all()
    user = db_session.get(User, "USR-002")
    assert user is not None
    assert verify_password("BuildWise123!", user.password_hash)
    assert not verify_password("ShouldNotPersist123!", user.password_hash)


def test_current_user_can_update_profile_but_not_identity_fields(client, db_session):
    headers = login(client, "safety")

    updated = client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={"real_name": "更新后的安全员", "phone": "13800000000"},
    )

    assert updated.status_code == 200
    assert updated.json()["data"] == {
        "id": "USR-002",
        "username": "safety",
        "real_name": "更新后的安全员",
        "role": "safety_officer",
        "phone": "13800000000",
        "is_active": True,
    }

    forbidden_fields = client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={"username": "renamed", "role": "admin", "is_active": False},
    )
    assert forbidden_fields.status_code == 422

    user = db_session.get(User, "USR-002")
    assert user is not None
    assert user.username == "safety"
    assert user.role == "safety_officer"
    assert user.is_active is True


def test_current_user_can_change_password_with_audited_action_only(client, db_session):
    headers = login(client, "safety")
    before = db_session.query(AuditLog).count()

    changed = client.post(
        "/api/v1/users/me/password",
        headers=headers,
        json={
            "current_password": "BuildWise123!",
            "new_password": "NewBuildWise123!",
            "new_password_confirm": "NewBuildWise123!",
        },
    )

    assert changed.status_code == 200
    assert changed.json()["data"] == {"changed": True}
    assert db_session.query(AuditLog).count() == before + 1
    row = db_session.query(AuditLog).filter(AuditLog.action == "change_password").one()
    assert row.user_id == "USR-002"
    assert row.detail_json == {}

    old_password = client.post("/api/v1/auth/login", json={"username": "safety", "password": "BuildWise123!"})
    assert old_password.status_code == 401
    new_password = client.post("/api/v1/auth/login", json={"username": "safety", "password": "NewBuildWise123!"})
    assert new_password.status_code == 200


def test_password_change_requires_current_password_and_matching_long_password(client, db_session):
    headers = login(client, "safety")

    wrong_current = client.post(
        "/api/v1/users/me/password",
        headers=headers,
        json={"current_password": "wrong-password", "new_password": "NewBuildWise123!", "new_password_confirm": "NewBuildWise123!"},
    )
    assert wrong_current.status_code == 400
    assert wrong_current.json()["error"]["code"] == "AUTH_CURRENT_PASSWORD_INVALID"

    mismatch = client.post(
        "/api/v1/users/me/password",
        headers=headers,
        json={"current_password": "BuildWise123!", "new_password": "NewBuildWise123!", "new_password_confirm": "Different123!"},
    )
    assert mismatch.status_code == 422

    too_short = client.post(
        "/api/v1/users/me/password",
        headers=headers,
        json={"current_password": "BuildWise123!", "new_password": "short", "new_password_confirm": "short"},
    )
    assert too_short.status_code == 422
    assert db_session.query(AuditLog).filter(AuditLog.action == "change_password").count() == 0
