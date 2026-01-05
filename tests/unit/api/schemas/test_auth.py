import pytest
from pydantic import ValidationError
from app.api.schemas.auth import Token


@pytest.mark.parametrize(
    "input_data, expected",
    [
        pytest.param(
            {"access_token": "abc123", "token_type": "bearer"},
            {"access_token": "abc123", "token_type": "bearer"},
            id="valid token"
        ),
        pytest.param(
            {"access_token": "xxx"},
            {"access_token": "xxx", "token_type": "bearer"},
            id="default token_type"
        ),
        pytest.param(
            {"access_token": ""},
            {"access_token": "", "token_type": "bearer"},
            id="empty access_token valid"
        ),
    ]
)
def test_token_valid(input_data, expected):
    """Проверяем валидные токены"""
    token = Token(**input_data)
    assert token.access_token == expected["access_token"]
    assert token.token_type == expected["token_type"]


@pytest.mark.parametrize(
    "input_data, error_msg",
    [
        pytest.param(
            {},
            "Field required",
            id="missing all fields"
        ),
        pytest.param(
            {"access_token": None},
            "Input should be a valid string",
            id="access_token None"
        ),
        pytest.param(
            {"access_token": "abc", "token_type": None},
            "Input should be a valid string",
            id="token_type None"
        ),
    ]
)
def test_token_invalid(input_data, error_msg):
    """Проверяем невалидные токены"""
    with pytest.raises(ValidationError, match=error_msg):
        Token(**input_data)
