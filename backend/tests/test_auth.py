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
