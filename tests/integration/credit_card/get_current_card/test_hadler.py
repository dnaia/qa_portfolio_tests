from app.external.db.models import CreditCardModel, UserModel
from sqlalchemy import select

from tests.conftest import session, add_test_user, create_test_credit_card


async def test_get_card_information_200(cli, auth_header, session, add_test_user, requested_limit,
                                        create_test_credit_card):
    """Тест на успешное получение информации по карте"""
    card = create_test_credit_card

    # Получаем карту через GET
    resp = await cli.get(url='/credit_card', headers=auth_header)
    assert resp.status_code == 200
    data = resp.json()

    # Проверяем данные
    assert data['limit'] == card.limit
    assert data['balance'] == card.balance
    assert data['active'] == card.active
    assert data['exp_date'] == card.exp_date.isoformat()


async def test_get_card_information_without_card_400(cli, auth_header, session, add_test_user, requested_limit):
    """Тест на получение информации по несуществующей карте"""
    resp = await cli.get(url='/credit_card', headers=auth_header)
    assert resp.status_code == 400
    data = resp.json()

    user_id = add_test_user.id

    result = await session.execute(
        select(CreditCardModel).where(CreditCardModel.user_id == user_id)
    )
    cards = result.scalars().all()

    assert len(cards) == 0
    assert data['detail'] == "Карты нет, сначала надо открыть."


async def test_get_card_information_with_invalid_token_403(cli, invalid_header, session, add_test_user, requested_limit,
                                                           create_test_credit_card):
    """Проверка получения информации по кредитной карты с несуществующем токеном"""
    card = create_test_credit_card
    resp = await cli.get(url='/credit_card', headers=invalid_header)
    assert resp.status_code == 403
    resp_data = resp.json()
    assert resp_data['detail'] == "Невозможно провалидировать токен."


async def test_get_card_information_not_found_404(cli, auth_header_deleted_user, requested_limit,
                                                  create_test_credit_card):
    """Проверка получения информации по кредитной карты с удаленным пользователем"""
    resp = await cli.get(url="/credit_card", headers=auth_header_deleted_user)

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Пользователь не найден."
