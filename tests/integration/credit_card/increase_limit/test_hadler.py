import logging

import pytest

from app.external.db.models import CreditCardModel, UserModel
from sqlalchemy import select

from tests.conftest import session, requested_limit, add_test_user, assert_no_cards


async def test_increase_limit_card_204(
        cli, auth_header, session, requested_limit, add_test_user, create_test_credit_card, random_user_payload, caplog
):
    """Проверка успешного увеличения лимита кредитной карты"""

    caplog.set_level(logging.ERROR)

    # 1. Обновляем данные пользователя, чтобы get_limit работал корректно
    resp_update = await cli.patch(
        url="/user",
        json=random_user_payload,
        headers=auth_header
    )
    assert resp_update.status_code == 204

    # 2. Создаём карту
    card = create_test_credit_card

    # 3. Увеличиваем лимит
    resp = await cli.post(
        url="/credit_card/increase_limit",
        headers=auth_header,
        params={"limit": requested_limit},
    )

    assert resp.status_code == 200

    # 4. Проверяем итог
    result = await session.execute(
        select(CreditCardModel).where(CreditCardModel.user_id == add_test_user.id)
    )
    card = result.scalars().one()

    assert card.limit >= 20_000_00
    assert card.balance is not None
    assert card.active is True

    assert not caplog.messages


async def test_increase_limit_without_card_400(
        cli, auth_header, session, requested_limit, add_test_user, create_test_credit_card, random_user_payload,
        assert_no_cards
):
    """Проверка попытки увеличения лимита кредитной карты без открытой карты"""

    # 1. Увеличиваем лимит
    resp = await cli.post(
        url="/credit_card/increase_limit",
        headers=auth_header,
        params={"limit": requested_limit},
    )

    assert resp.status_code == 400

    # 2. Проверяем итог
    result = await session.execute(
        select(CreditCardModel).where(CreditCardModel.user_id == add_test_user.id)
    )
    card = result.scalars().one()
    data = resp.json()

    assert assert_no_cards()
    assert data[
               "detail"] == "Увеличение лимита недоступно с текущими параметрами. Для увеличения попробуйте дополнить информацию о себе."
    # Очень странный ответ для человека без карты


async def test_increase_limit_with_closed_card_400(
        cli,
        auth_header,
        session,
        requested_limit,
        add_test_user,
        close_test_credit_card,
):
    """Проверка попытки увеличения лимита закрытой кредитной карты"""

    resp = await cli.post(
        url="/credit_card/increase_limit",
        headers=auth_header,
        params={"limit": requested_limit},
    )

    assert resp.status_code == 400
    data = resp.json()

    assert data["detail"] == "Карта неактивна."

    # Проверяем, что карта в БД всё ещё одна и закрытая
    result = await session.execute(
        select(CreditCardModel).where(CreditCardModel.user_id == add_test_user.id)
    )
    cards = result.scalars().all()

    assert len(cards) == 1

    card = cards[0]
    assert card.id == close_test_credit_card.id
    assert card.active is False
    # Лимит и баланс не изменились
    assert card.limit == close_test_credit_card.limit
    assert card.balance == close_test_credit_card.balance


async def test_increase_limit_with_invalid_token_403(
        cli,
        invalid_header,
        session,
        requested_limit,
        add_test_user,
        assert_no_cards
):
    """Проверка увеличения лимита с неверным токеном"""

    resp = await cli.post(
        url="/credit_card/increase_limit",
        headers=invalid_header,
        params={"limit": requested_limit},
    )

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Невозможно провалидировать токен."

    # Проверяем, что никакой карты не создано
    assert assert_no_cards()


async def test_increase_limit_user_not_found_404(
        cli,
        auth_header_deleted_user,
        requested_limit,
        session,
        add_test_user,
        assert_no_cards):
    """Проверка увеличения лимита для удалённого пользователя"""

    resp = await cli.post(
        url="/credit_card/increase_limit",
        headers=auth_header_deleted_user,
        params={"limit": requested_limit},
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Пользователь не найден."

    # Убеждаемся, что даже если была карта — сейчас ничего нет
    assert assert_no_cards()


@pytest.mark.parametrize('limit',
                         [
                             pytest.param(0, id="zero"),
                             pytest.param("пятьдесят тысяч", id="str"),
                             pytest.param(None, id="None"),
                         ])
async def test_increase_limit_card_validation_error_422(
        cli, auth_header, session, add_test_user, create_test_credit_card, random_user_payload
        , limit):
    """Проверка невалидных полей увеличения лимита кредитной карты"""

    # 1. Обновляем данные пользователя, чтобы get_limit работал корректно
    resp_update = await cli.patch(
        url="/user",
        json=random_user_payload,
        headers=auth_header
    )
    assert resp_update.status_code == 204

    # 2. Создаём карту
    new_card = create_test_credit_card

    # 3. Увеличиваем лимит
    resp = await cli.post(
        url="/credit_card/increase_limit",
        headers=auth_header,
        params={"limit": limit},
    )

    assert resp.status_code == 422

    # 4. Проверяем итог
    result = await session.execute(
        select(CreditCardModel).where(CreditCardModel.user_id == add_test_user.id)
    )
    card = result.scalars().one()

    assert card.limit == new_card.limit
