import datetime

import pytest
from dateutil.relativedelta import relativedelta

from app.api.schemas.common import Sex
from app.external.db.models import UserModel
from sqlalchemy import select

from tests.conftest import session, add_test_user, create_test_credit_card


async def test_get_user_200(cli, auth_header, add_test_user, session):
    """Проверка получения информации о пользователе и сравнения полученной информации с информацией в БД"""
    resp = await cli.get(url='/user', headers=auth_header)
    assert resp.status_code == 200
    data = resp.json()
    assert data['email'] == add_test_user.email
    result = await session.scalars(select(UserModel).where(UserModel.email == add_test_user.email))
    users = result.all()
    assert len(users) == 1

    user = users[0]

    assert user.full_name == data["full_name"]
    assert user.income == data["income"]
    assert user.another_loans == data["another_loans"]
    assert user.birth_date == data["birth_date"]
    assert user.sex == data["sex"]
    assert user.email == data["email"]
    assert user.status_document == data["status_document"]
    assert user.status_face == data["status_face"]


async def test_get_user_with_invalid_token_403(cli, invalid_header, session, add_test_user, requested_limit,
                                               create_test_credit_card, random_user_payload):
    """Тест на получение информации по пользователю c некорректным токеном"""
    resp = await cli.get(url='/user', headers=invalid_header)
    assert resp.status_code == 403
    resp_data = resp.json()
    assert resp_data['detail'] == "Невозможно провалидировать токен."


async def test_get_user_not_found_404(cli, auth_header_deleted_user):
    """Проверка получения информации по пользователю, которого нет в БД"""

    resp = await cli.get("/user", headers=auth_header_deleted_user)

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Пользователь не найден."


@pytest.mark.add_test_user_data(
    {
        'full_name': 'Some Big Name',
        'income': 500_00,
        'another_loans': True,
        'birth_date': datetime.date.today() - relativedelta(years=21),
        'sex': Sex.male,
    }
)
async def test_user(cli, auth_header, add_test_user):
    """Проверка получения текущего пользователя"""
    resp = await cli.get(url='/user', headers=auth_header)

    assert resp.status_code == 200
    resp_data = resp.json()

    assert resp_data['another_loans'] == add_test_user.another_loans
    assert resp_data['full_name'] == add_test_user.full_name
    assert resp_data['income'] == add_test_user.income
    assert resp_data['birth_date'] == add_test_user.birth_date.isoformat()
    assert resp_data['sex'] == add_test_user.sex.value
    assert resp_data['email'] == add_test_user.email
    assert resp_data['status_document'] == add_test_user.status_document
    assert resp_data['status_face'] == add_test_user.status_face
