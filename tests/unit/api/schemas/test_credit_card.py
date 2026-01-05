import datetime

import pytest
from pydantic_core import ValidationError

from app.api.schemas.credit_card import CreditCard


# 1) Позитивные случаи
@pytest.mark.parametrize(
    ("limit", "balance", "active", "exp_date"),
    [
        pytest.param(1, 1, True, datetime.date(2030, 1, 1), id="min valid fields"),
        pytest.param(500_000_00, 100_000_00, False, datetime.date(2035, 5, 5), id="max values + inactive"),
    ]
)
def test_CreditCard_schema(limit, balance, active, exp_date):
    card = CreditCard(
        limit=limit,
        balance=balance,
        active=active,
        exp_date=exp_date
    )

    assert card.limit == limit
    assert card.balance == balance
    assert card.active == active
    assert card.exp_date == exp_date


# 2) Позитивная JSON-инициализация
@pytest.mark.parametrize(
    ("create_request", "expected_card"),
    [
        pytest.param(
            {
                "limit": 100_00,
                "balance": 100_00,
                "active": True,
                "exp_date": "2030-01-01",
            },
            CreditCard(limit=100_00, balance=100_00, active=True, exp_date=datetime.date(2030, 1, 1)),
            id="valid_json",
        ),
        pytest.param(
            {
                "limit": 500_000_00,
                "balance": 10_000_00,
                "active": False,
                "exp_date": "2025-12-31",
            },
            CreditCard(limit=500_000_00, balance=10_000_00, active=False, exp_date=datetime.date(2025, 12, 31)),
            id="valid_json_large_values",
        ),
    ]
)
def test_CreditCard_schema_json(create_request, expected_card):
    assert CreditCard(**create_request) == expected_card


# 3) Ошибки валидации при передаче параметров напрямую
@pytest.mark.parametrize(
    ("limit", "balance", "active", "exp_date", "message"),
    [
        pytest.param(0, 100, True, datetime.date(2030, 1, 1),
                     "Input should be greater than 0", id="limit_zero"),
        pytest.param(-1, 100, True, datetime.date(2030, 1, 1),
                     "Input should be greater than 0", id="limit_negative"),
        pytest.param(100, 0, True, datetime.date(2030, 1, 1),
                     "Input should be greater than 0", id="balance_zero"),
        pytest.param(100, -10, True, datetime.date(2030, 1, 1),
                     "Input should be greater than 0", id="balance_negative"),
        pytest.param(100, 100, True, None,
                     "Input should be a valid date", id="exp_date_none"),
        pytest.param(100, 100, True, "bad_date",
                     "Input should be a valid date or datetime", id="exp_date_invalid"),
    ]
)
def test_CreditCard_schema_validation_error(limit, balance, active, exp_date, message):
    with pytest.raises(ValidationError, match=message):
        CreditCard(
            limit=limit,
            balance=balance,
            active=active,
            exp_date=exp_date,
        )


# 4) Ошибки валидации JSON
@pytest.mark.parametrize(
    ("create_request", "message"),
    [
        pytest.param(
            {"limit": 0, "balance": 100, "exp_date": "2030-01-01"},
            "Input should be greater than 0",
            id="limit_zero_json",
        ),
        pytest.param(
            {"limit": -5, "balance": 100, "exp_date": "2030-01-01"},
            "Input should be greater than 0",
            id="limit_negative_json",
        ),
        pytest.param(
            {"limit": 100, "balance": 0, "exp_date": "2030-01-01"},
            "Input should be greater than 0",
            id="balance_zero_json",
        ),
        pytest.param(
            {"limit": 100, "balance": "bad", "exp_date": "2030-01-01"},
            "Input should be a valid integer",
            id="balance_not_int_json",
        ),
        pytest.param(
            {"limit": 100, "balance": 100, "exp_date": "not-date"},
            "Input should be a valid date or datetime",
            id="exp_date_invalid_format_json",
        ),
    ]
)
def test_CreditCard_schema_validation_error_json(create_request, message):
    with pytest.raises(ValidationError, match=message):
        CreditCard(**create_request)
