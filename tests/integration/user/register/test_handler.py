import logging

from sqlalchemy import select

from app.external.db.models import UserModel


async def test_register_new_user_200(
        cli,
        session,
        test_user_password,
        test_user_email,
        delete_registered_user,
        caplog,
):
    """Проверка регистрации нового пользователя"""
    caplog.set_level(logging.ERROR)

    resp = await cli.post(
        url='/user/register',
        json={
            'email': test_user_email,
            'password': test_user_password,
        }
    )

    assert resp.status_code == 200
    resp_data = resp.json()
    assert resp_data['detail'] == 'success'

    result = await session.scalars(select(UserModel).where(UserModel.email == test_user_email))
    users = result.all()

    assert len(users) == 1

    user = users[0]
    assert user.email == test_user_email
    assert user.hashed_password is not None
    assert user.hashed_password != test_user_password
    assert user.full_name is None
    assert user.income is None
    assert user.another_loans is None
    assert user.birth_date is None
    assert user.sex is None
    assert user.status_face is False
    assert user.status_document is False

    assert not caplog.messages


async def test_register_existing_user_400(session, cli, add_test_user, caplog):
    """Проверка регистрации пользователя с уже существующим в системе email'ом"""
    existing_user_email = add_test_user.email
    resp = await cli.post(
        url='/user/register',
        json={
            'email': existing_user_email,
            'password': 'password',
        }
    )

    assert resp.status_code == 400
    resp_data = resp.json()
    assert resp_data['detail'] == 'Пользователь с таким адресом электронной почты уже существует.'

    result = await session.scalars(select(UserModel).where(UserModel.email == existing_user_email))
    users = result.all()
    assert len(users) == 1

    assert 'HTTP Request: POST http://testserver/user/register "HTTP/1.1 400 Bad Request"' in caplog.messages


async def test_register_user_with_invalid_email_422(session, cli):
    """Проверка регистрации пользователя с невалидным email'ом"""
    invalid_email = 'hello_email.ru'

    resp = await cli.post(
        url='/user/register',
        json={
            'email': invalid_email,
            'password': 'password',
        }
    )

    assert resp.status_code == 422
    resp_data = resp.json()
    assert resp_data['detail'] == [
        {
            "type": "value_error",
            "loc": [
                "body",
                "email"
            ],
            "msg": "value is not a valid email address: An email address must have an @-sign.",
            "input": invalid_email,
            "ctx": {
                "reason": "An email address must have an @-sign."
            }
        }
    ]

    result = await session.scalars(select(UserModel).where(UserModel.email == invalid_email))
    assert not result.all()
