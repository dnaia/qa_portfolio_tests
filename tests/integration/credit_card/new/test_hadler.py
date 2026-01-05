import logging

import pytest

from app.external.db.models import CreditCardModel
from sqlalchemy import select

from tests.conftest import session, requested_limit, add_test_user, assert_no_cards


async def test_new_card_200(cli, auth_header, session, requested_limit, add_test_user, caplog):
    """Проверка успешного открытия новой кредитной карты"""
    caplog.set_level(logging.ERROR)

    resp = await cli.post(
        url='/credit_card/new',
        headers=auth_header,
        params={"limit": requested_limit},
    )

    assert resp.status_code == 200

    # берем user_id из существующей тестовой карты
    user_id = add_test_user.id

    result = await session.execute(
        select(CreditCardModel).where(CreditCardModel.user_id == user_id)
    )
    cards = result.scalars().all()

    assert len(cards) == 1

    card = cards[0]
    assert card.id is not None
    assert card.user_id == user_id
    assert card.limit >= 20_000_00
    assert card.balance is not None
    assert card.active is True
    assert card.exp_date is not None

    assert not caplog.messages


async def test_new_second_card_400(create_card, add_test_credit_card, add_test_user, session):
    """Проверка открытия второй кредитной карты"""
    resp = await create_card()
    assert resp.status_code == 400
    assert resp.json()["detail"] == "У пользователя уже есть кредитная карта."

    # берем user_id из существующей тестовой карты
    user_id = add_test_user.id

    result = await session.execute(
        select(CreditCardModel).where(CreditCardModel.user_id == user_id)
    )
    cards = result.scalars().all()

    assert len(cards) == 1

    card = cards[0]
    assert card.id is not None
    assert card.user_id == user_id
    assert card.balance is not None
    assert card.active is True
    assert card.exp_date is not None


async def test_new_card_with_invalid_token_403(cli, invalid_header, session, add_test_user, requested_limit):
    """Проверка открытия кредитной карты с несуществующем токеном"""
    resp = await cli.post(url='/credit_card/new', headers=invalid_header, params={"limit": requested_limit})

    assert resp.status_code == 403
    resp_data = resp.json()
    assert resp_data['detail'] == "Невозможно провалидировать токен."

    user_id = add_test_user.id

    result = await session.execute(
        select(CreditCardModel).where(CreditCardModel.user_id == user_id)
    )
    cards = result.scalars().all()

    assert len(cards) == 0


async def test_new_card_user_not_found_404(cli, auth_header_deleted_user, requested_limit):
    """Проверка открытия кредитной карты с удаленным пользователем"""
    resp = await cli.post("/credit_card/new", headers=auth_header_deleted_user, params={"limit": requested_limit})

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Пользователь не найден."


async def test_new_card_with_invalid_limit_422(cli, auth_header, create_card, assert_no_cards):
    """Проверка открытия кредитной карты с неверным лимитом"""
    limit = "тридцать тысяч"
    resp = await create_card(limit=limit)

    assert resp.status_code == 422
    resp_data = resp.json()
    expected = {
        "type": "int_parsing",
        "loc": ["query", "limit"],
        "msg": "Input should be a valid integer, unable to parse string as an integer",
        "input": limit,
    }

    # Проверяем только обязательные ключи
    for k, v in expected.items():
        assert resp_data["detail"][0].get(k) == v

    assert assert_no_cards()


@pytest.mark.xfail(reason="Повторное открытие карты",
                   raises=AssertionError)  # БР-10.5, ОР: 200, ФР: 400 (card.active == False, ожидалось True)
async def test_new_card_after_closed_first_card_200(cli, auth_header, session, requested_limit, add_test_user):
    """Проверка успешного открытия новой кредитной карты, после закрытия старой"""
    resp = await cli.post(
        url='/credit_card/new',
        headers=auth_header,
        params={"limit": requested_limit},
    )

    resp = await cli.post(url='/credit_card/close', headers=auth_header)

    resp = await cli.post(
        url='/credit_card/new',
        headers=auth_header,
        params={"limit": requested_limit},
    )
    # берем user_id из существующей тестовой карты
    user_id = add_test_user.id

    result = await session.execute(
        select(CreditCardModel).where(CreditCardModel.user_id == user_id)
    )
    cards = result.scalars().all()

    assert len(cards) == 1
    assert resp.status_code == 200
    card = cards[0]
    assert card.active is True
