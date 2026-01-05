import pytest


async def test_auth_correct_user_200(cli, test_user_email, test_user_password, add_test_user):
    """Успешная авторизация"""

    resp = await cli.post(
        "/auth/access_token",
        data={"username": test_user_email, "password": test_user_password},
    )

    assert resp.status_code == 200
    data = resp.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_auth_incorrect_user_400(cli):
    """Неверный логин или пароль"""

    resp = await cli.post(
        "/auth/access_token",
        data={"username": "unknown@example.com", "password": "wrongpass"},
    )

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Некорркетный адрес почты или пароль."


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({}, id="None"),
        pytest.param(
            {"username": "user@example.com"}, id="No password"),
        pytest.param(
            {"password": "abc"}, id="No username"),
    ],
)
async def test_auth_validation_error_422(cli, payload):
    """Ошибка валидации входных данных"""

    resp = await cli.post("/auth/access_token", data=payload)

    assert resp.status_code == 422

    detail = resp.json()["detail"]
    assert isinstance(detail, list)
