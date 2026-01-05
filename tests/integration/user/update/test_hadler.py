import logging

from sqlalchemy import select

from app.external.db.models import UserModel, CreditCardModel


async def test_update_user_204(
        cli,
        session,
        test_user_password,
        test_user_email,
        delete_registered_user,
        caplog,
        random_user_payload, auth_header):
    """Проверка обновления информации о пользователе"""
    caplog.set_level(logging.ERROR)

    resp = await cli.patch(
        url='/user',
        json=random_user_payload, headers=auth_header)

    assert resp.status_code == 204

    result = await session.scalars(select(UserModel).where(UserModel.email == test_user_email))
    users = result.all()

    assert len(users) == 1

    user = users[0]
    assert user.email == test_user_email
    assert user.hashed_password is not None
    assert user.hashed_password != test_user_password
    assert user.full_name == random_user_payload['full_name']
    assert user.income == random_user_payload['income']
    assert user.another_loans == random_user_payload['another_loans']
    assert user.birth_date.isoformat() == random_user_payload["birth_date"]
    assert user.sex.value == random_user_payload["sex"]
    assert user.status_face == False
    assert user.status_document == False

    assert not caplog.messages


async def test_update_user_with_invalid_token_403(cli, invalid_header, session, random_user_payload, add_test_user):
    """Проверка обновления информации о пользователе с несуществующем токеном"""
    resp = await cli.patch(
        url='/user',
        json=random_user_payload, headers=invalid_header)

    assert resp.status_code == 403
    resp_data = resp.json()
    assert resp_data['detail'] == "Невозможно провалидировать токен."

    user_id = add_test_user.id

    result = await session.execute(
        select(CreditCardModel).where(CreditCardModel.user_id == user_id)
    )
    cards = result.scalars().all()

    assert len(cards) == 0


async def test_update_user_not_found_404(cli, auth_header_deleted_user, requested_limit, random_user_payload):
    """Проверка обновления информации о пользователе с ненайденным пользователем"""
    resp = await cli.patch(
        url='/user',
        json=random_user_payload, headers=auth_header_deleted_user)

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Пользователь не найден."


async def test_new_card_with_invalid_limit_422(cli, auth_header, create_card, assert_no_cards, random_user_payload,
                                               session, test_user_email):
    """Проверка обновлении информации с невалидными данными"""
    result = await session.scalars(select(UserModel).where(UserModel.email == test_user_email))
    users = result.all()
    user = users[0]
    resp = await cli.patch(
        url='/user',
        json={
            "full_name": None,
            "income": None,
            "another_loans": -100,
            "birth_date": None,
            "sex": 'N',
        }, headers=auth_header)

    assert resp.status_code == 422
    result_after_update = await session.scalars(select(UserModel).where(UserModel.email == test_user_email))
    users_after_update = result_after_update.all()
    user_after_update = users_after_update[0]
    resp_data = resp.json()
    expected = {
        "type": "bool_parsing",
        "loc": ['body', 'another_loans'],
        "msg": 'Input should be a valid boolean, unable to interpret input',
        "input": -100,
    }

    # Проверяем только обязательные ключи
    for k, v in expected.items():
        assert resp_data["detail"][0].get(k) == v

    assert assert_no_cards()

    # Проверка, что БД не обновилась
    assert user_after_update == user
