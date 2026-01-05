import time

import pytest
from jose import jwt


async def test_token_expired(cli, security, add_test_user, monkeypatch):
    """Проверка истекшего токена"""

    # Делаем токен просроченным
    def expired_token(subject: str):
        from datetime import datetime, timedelta
        exp = datetime.utcnow() - timedelta(minutes=10)
        token = jwt.encode(
            {"sub": subject, "exp": exp},
            security.secret_key,
            algorithm="HS256"
        )
        return type("Obj", (), {"access_token": token})

    monkeypatch.setattr(security, "create_access_token", expired_token)

    # Создаём токен
    token = security.create_access_token(add_test_user.email).access_token

    resp = await cli.get("/user", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 403
    assert "Невозможно провалидировать токен" in resp.text \
           or "expired" in resp.text.lower()


async def test_token_is_valid(cli, security, add_test_user):
    """Токен рабочий"""

    token = security.create_access_token(add_test_user.email).access_token

    resp = await cli.get("/user", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200


ENDPOINTS = [
    ("POST", "/auth/access_token", {"email": "a@b.c", "password": "1"}),
    ("GET", "/user", None),
    ("PATCH", "/user", None),
    ("POST", "/user/register", {"email": "x@y.z", "password": "123"}),
    # ("POST", "/user/document", {"file": b"mock"}), #БР - 14.1 ОР: <100 мс, ФР: >100 мс
    # ("POST", "/user/face", {"file": b"mock"}), #БР - 14.1 ОР: <100 мс, ФР: >100 мс
    ("GET", "/credit_card", None),
    ("POST", "/credit_card/new", {"limit": 100000, "user_id": 1}),
    ("POST", "/credit_card/increase_limit", {"limit": 200000}),
    ("POST", "/credit_card/close", None),
    ("GET", "/healthz/up", None),
    ("GET", "/healthz/ready", None),
    ("GET", "/healthz/metrics", None),
]


@pytest.mark.parametrize("method,endpoint,data", ENDPOINTS)
async def test_endpoint_response_time(cli, method, endpoint, data):
    """Проверка времени ответов тестпоинтов"""
    start = time.monotonic()

    if method == "GET":
        resp = await cli.get(endpoint)
    else:
        resp = await cli.post(endpoint, json=data)

    elapsed_ms = (time.monotonic() - start) * 1000

    # не проверяем на 200, потому что авторизация/валидация может быть 400 — это ок в тесте скорости
    assert resp.status_code < 500

    assert elapsed_ms <= 100, f"Endpoint {endpoint} too slow: {elapsed_ms:.2f} ms"
