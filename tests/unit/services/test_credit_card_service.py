import datetime

import pytest
from dateutil.relativedelta import relativedelta

from app.external.db.models import UserModel, CreditCardModel
from app.services.credit_cards import CreditCardService


@pytest.mark.parametrize(('user', 'expected_amount'), [
    pytest.param(UserModel(), 20_000_00, id='user_without_data'),
    pytest.param(UserModel(full_name='Иванов Иван'), 25_000_00, id='user has full_name', marks=pytest.mark.xfail(
        reason="БАГ 11.6.1. ОР: 25.000, ФР: 21.000. БР-11.6.1")),
    pytest.param(UserModel(income=500_000_00), 120_000_00, id='user income > 300_000_00'),
    pytest.param(UserModel(income=300_000_00), 120_000_00, id='user income = 300_000_00'),
    pytest.param(UserModel(income=200_000_00), 30_000_00, id='user income > 100_000_00'),
    pytest.param(UserModel(income=100_000_01), 30_000_00, id='user income = 100_000_01'),
    pytest.param(UserModel(income=100_000_00), 30_000_00, id='user income = 100_000_00'),
    pytest.param(UserModel(income=99_999_99), 21_000_00, id='user income = 99_999_99'),
    pytest.param(UserModel(income=100_00), 21_000_00, id='user income = 100_00'),
    pytest.param(UserModel(income=0), 20_000_00, id='user income = 0'),
    pytest.param(UserModel(another_loans=False), 30_000_00, id='user with no other loans'),
    pytest.param(UserModel(another_loans=True), 20_000_00, id='user with other loans'),
    pytest.param(
        UserModel(income=300_000_00, another_loans=True),
        110_000_00,
        id='user income = 300_000_00 and other loans'
    ),
    pytest.param(
        UserModel(birth_date=(datetime.date.today() - relativedelta(years=15))),
        20_000_00,
        id='user with age < 18'  # БАГ 11.2.4. ОР: ValidationError ФР: 20.000
    ),
    pytest.param(
        UserModel(income=100_000_00, birth_date=(datetime.date.today() - relativedelta(years=15))),
        25_000_00,
        id='user income = 100_000_00 with age < 18'
    ),
    pytest.param(
        UserModel(birth_date=(datetime.date.today() - relativedelta(years=18) + relativedelta(days=1))),
        20_000_00,
        id='user with age is 1 day before 18'
    ),
    pytest.param(
        UserModel(birth_date=(datetime.date.today() - relativedelta(years=18))),
        22_000_00,
        id='user with age is 18'
    ),
    pytest.param(
        UserModel(birth_date=(datetime.date.today() - relativedelta(years=65))),
        20_000_00,
        id='user with age is 65'
    ),
    pytest.param(
        UserModel(birth_date=(datetime.date.today() - relativedelta(years=70))),
        20_000_00,
        id='user with age > 65'  # БАГ 11.2.4. ОР: ValidationError ФР: 20.000
    ),
    pytest.param(
        UserModel(status_document=True),
        25_000_00,
        id='status document is True'
    ),
    pytest.param(
        UserModel(status_face=True),
        25_000_00,
        id='status face is True'
    ),
    pytest.param(
        UserModel(status_document=True, status_face=True),
        30_000_00,
        id='status document, face == True'
    ),
    pytest.param(
        UserModel(status_face=None, status_document=None),
        20_000_00,
        id='status face and document == None'
    ),
    pytest.param(
        UserModel(sex="male"),
        20_000_00,
        id='min limit for male', marks=pytest.mark.xfail(
            reason="БАГ 11.1.1. ОР: 20.000, ФР: 22.000. БР-11.1.1")

    ),
    pytest.param(
        UserModel(sex="female"),
        40_000_00,
        id='min limit for female', marks=pytest.mark.xfail(
            reason="БАГ 11.1.2. ОР: 40.000, ФР: 22.000. БР-11.1.2")

    ),
    pytest.param(
        UserModel(sex="female", birth_date=(datetime.date.today() - relativedelta(years=35)), income=150_000_00,
                  another_loans=False, status_document=True, full_name="full_name"),
        72_000_00,
        id='scenario for female', marks=pytest.mark.xfail(
            reason="БАГ 11.8.1. ОР: 72.000, ФР: 50.000. БР-11.8.1")

    ),
])
def test_get_limit(user: UserModel, expected_amount, credit_card_service):
    result_amount = credit_card_service.get_limit(
        requested_limit=500_000_00,
        user=user
    )
    assert result_amount == expected_amount


@pytest.mark.parametrize(
    ("limit", "user_id"),
    [
        pytest.param(1, 1, id="valid_min_limit"),
        pytest.param(500_000_00, 25, id="valid_max_limit"),
        pytest.param(499_999_99, 2, id="valid"),
    ]
)
async def test_add_card(limit, user_id, credit_card_mock):
    card = await credit_card_mock.add(limit=limit, user_id=user_id)

    # проверяем, что модель создана корректно
    assert isinstance(card, CreditCardModel)
    assert card.limit == limit
    assert card.balance == limit
    assert card.user_id == user_id

    # exp_date установлена правильно
    assert card.exp_date.year == (credit_card_mock.exp_date.year)

    # проверяем, что запись пыталась сделаться
    sess = credit_card_mock.session_factory.return_value.__aenter__.return_value
    sess.add.assert_called_once()
    sess.refresh.assert_called_once_with(card)


@pytest.mark.parametrize(
    ("old_limit", "old_balance", "new_limit"),
    [
        pytest.param(10_000_00, 10_000_00, 20_000_00, id="increase_limit"),
        pytest.param(20_000_00, 20_000_00, 10_000_00, id="decrease_limit"),
        pytest.param(15_000_00, 15_000_00, 15_000_00, id="same_limit"),
    ]
)
async def test_update_limit(old_limit, old_balance, new_limit, credit_card_mock):
    card_db = CreditCardModel(
        limit=old_limit,
        balance=old_balance,
        exp_date=credit_card_mock.exp_date,
        user_id=1
    )

    updated_card = await credit_card_mock.update_limit(new_limit, card_db)

    # Проверяем правильность пересчёта
    diff = new_limit - old_limit
    assert updated_card.limit == new_limit
    assert updated_card.balance == old_balance + diff

    # Убедимся, что была попытка записи
    session = credit_card_mock.session_factory.return_value.__aenter__.return_value
    session.add.assert_called_once_with(card_db)
    session.refresh.assert_called_once_with(card_db)


@pytest.mark.parametrize(
    ("initial_limit", "initial_balance", "new_limit", "expected_balance"),
    [
        pytest.param(20_000_00, 20_000_00, 30_000_00, 30_000_00, id="increase"),
        pytest.param(30_000_00, 30_000_00, 25_000_00, 25_000_00, id="decrease"),
        pytest.param(10_000_00, 5_000_00, 20_000_00, 15_000_00, id="increase_with_partial_spend"),
    ],
)
async def test_update_limit_various_cases(
        credit_card_mock,
        initial_limit,
        initial_balance,
        new_limit,
        expected_balance,
):
    card = CreditCardModel(limit=initial_limit, balance=initial_balance)

    updated = await credit_card_mock.update_limit(new_limit, card)

    assert updated.limit == new_limit
    assert updated.balance == expected_balance


async def test_close_card(credit_card_mock):
    card_db = CreditCardModel(
        limit=10_000_00,
        balance=10_000_00,
        active=True,
        exp_date=credit_card_mock.exp_date,
        user_id=1
    )

    await credit_card_mock.close_card(card_db)

    assert card_db.active is False

    session = credit_card_mock.session_factory.return_value.__aenter__.return_value
    session.add.assert_called_once_with(card_db)


@pytest.mark.parametrize("available, requested, default, expected", [
    (5_000, 10_000_000, 20_000_00, 20_000_00),  # available меньше default
])
def test_get_limit_floor(credit_card_service, available, requested, default, expected):
    """Доступный меньше, чем стандартный = стандартный"""
    user = UserModel(income=None, full_name=None)  # даст минимальный available_limit
    credit_card_service.default_limit = default

    result = credit_card_service.get_limit(requested, user)
    assert result == expected


def test_get_limit_capped_by_requested_limit(credit_card_service):
    """Запрашиваемый лимит меньше, чем доступный = доступный"""
    user = UserModel(full_name="Full Name", income=500_000_00)
    requested_limit = 5_000_00  # меньше чем available_limit

    result = credit_card_service.get_limit(requested_limit, user)
    assert result == 20_000_00  # БАГ БР-8.7 возвращает доступный лимит


def test_get_limit_default_is_higher_than_requested(credit_card_service):
    credit_card_service.default_limit = 50_000_00
    user = UserModel()

    result = credit_card_service.get_limit(10_000_00, user)
    assert result == 50_000_00


def test_get_limit_requested_too_high(credit_card_service):
    user = UserModel(full_name="user")  # available = default + 1_000_00

    requested_limit = 1_000_000_000  # огромный
    result = credit_card_service.get_limit(requested_limit, user)

    expected = credit_card_service.default_limit + 1_000_00
    assert result == expected


def test_get_limit_sex_none(credit_card_service):
    """sex=None — сервис не добавляет бонусы."""
    user = UserModel(sex=None)
    result = credit_card_service.get_limit(999_000_00, user)
    assert result == credit_card_service.default_limit


def test_get_limit_invalid_sex_treated_as_female(credit_card_service):
    """Некорректный sex попадает в ветку female (баг сервиса)."""
    user = UserModel(sex="robot")

    result = credit_card_service.get_limit(999_000_00, user)

    # female добавляет 2_000_00
    assert result == credit_card_service.default_limit + 2_000_00


def test_get_limit_age_61(credit_card_service):
    """Возраст 61 уменьшение лимита."""
    user = UserModel(full_name=None, income=500_000_00,
                     birth_date=datetime.date.today() - relativedelta(years=61), status_face=None, status_document=None,
                     sex=None, another_loans=None,
                     )

    result = credit_card_service.get_limit(999_000_00, user)

    assert result == 115_000_00


def test_get_limit_age_60(credit_card_service):
    """Возраст 60 добавляет +2_000_00."""
    user = UserModel(
        birth_date=datetime.date.today() - relativedelta(years=60)
    )

    result = credit_card_service.get_limit(999_000_00, user)

    assert result == credit_card_service.default_limit + 2_000_00


def test_get_limit_all_equal():
    """Проверка max(min(available, requested), default)."""
    service = CreditCardService(
        session_factory=None,
        exp_date_in_years=1,
        default_limit=20_000_00
    )

    user = UserModel()  # available = default

    result = service.get_limit(
        requested_limit=20_000_00,
        user=user
    )

    assert result == 20_000_00


async def test_add_calls_session_begin_and_add(credit_card_mock):
    """Проверяет, что add вызывает session.begin()."""
    await credit_card_mock.add(limit=100_00, user_id=1)

    session = credit_card_mock.session_factory.return_value.__aenter__.return_value
    session.begin.assert_called_once()


async def test_update_limit_calls_session_begin(credit_card_mock):
    """Проверяет вызов session.begin() в update_limit."""
    card = CreditCardModel(limit=100, balance=100)
    await credit_card_mock.update_limit(200, card)

    session = credit_card_mock.session_factory.return_value.__aenter__.return_value
    session.begin.assert_called_once()


async def test_close_card_calls_session_begin(credit_card_mock):
    """Проверяет вызов session.begin() при закрытии карты."""
    card = CreditCardModel(limit=100, balance=100, active=True)

    await credit_card_mock.close_card(card)

    session = credit_card_mock.session_factory.return_value.__aenter__.return_value
    session.begin.assert_called_once()
