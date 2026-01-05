import pytest

from app.external.db.models import CreditCardModel
from sqlalchemy import select


async def test_close_200(cli, auth_header, add_test_credit_card, session, add_test_user):
    """Проверка закрытия кредитной карты клиента"""
    resp = await cli.post(url='/credit_card/close', headers=auth_header)

    assert resp.status_code == 200
    resp_data = resp.json()
    assert resp_data['detail'] == 'closed'
    user_id = add_test_user.id
    credit_card = await session.get(CreditCardModel, add_test_credit_card.id)

    assert credit_card.id is not None
    assert credit_card.user_id == user_id
    assert credit_card.limit is not None
    assert credit_card.balance is not None
    assert credit_card.active is False
    assert credit_card.exp_date is not None


async def test_close_without_active_card_400(cli, auth_header, session, add_test_user):
    """Проверка закрытия несуществующей кредитной карты клиента"""

    resp = await cli.post(url='/credit_card/close', headers=auth_header)

    assert resp.status_code == 400
    resp_data = resp.json()
    assert resp_data['detail'] == "Карты нет, сначала надо открыть."

    # Проверяем, что у пользователя действительно нет карты
    result = await session.execute(
        select(CreditCardModel).where(CreditCardModel.user_id == add_test_user.id)
    )
    credit_card = result.scalars().first()

    assert credit_card is None


async def test_close_card_with_invalid_token_403(cli, invalid_header, session, add_test_user):
    """Проверка закрытия кредитной карты с несуществующем токеном"""

    resp = await cli.post(url='/credit_card/close', headers=invalid_header)

    assert resp.status_code == 403
    resp_data = resp.json()
    assert resp_data['detail'] == "Невозможно провалидировать токен."

    # Проверяем, что у пользователя действительно нет карты и никаких изменений не произошло
    result = await session.execute(
        select(CreditCardModel).where(CreditCardModel.user_id == add_test_user.id)
    )
    credit_card = result.scalars().first()

    # Т.к. мы карту не создавали — её ждать не должны
    assert credit_card is None


async def test_close_card_user_not_found_404(cli, auth_header_deleted_user):
    """Проверка закрытия кредитной карты с удаленным пользователем"""
    resp = await cli.post("/credit_card/close", headers=auth_header_deleted_user)

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Пользователь не найден."


@pytest.mark.xfail(reason="Повторное закрытие карты", raises=AssertionError)  # БР-10.5, ОР: 400, ФР: 200
async def test_close_card_when_already_closed(cli, auth_header, close_test_credit_card):
    """Попытка закрыть повторно кредитную карту"""
    resp = await cli.post('/credit_card/close', headers=auth_header)
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Карта уже закрыта."
