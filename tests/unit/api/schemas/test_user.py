import datetime

import pytest
from pydantic_core import ValidationError

from app.api.schemas.common import Sex
from app.api.schemas.user import UserCreate, UserUpdate


@pytest.mark.parametrize(('email', 'password'), [
    pytest.param('valid@email.cft', 'user_password', id='valid user to create'),
    pytest.param('valid@email.cft', '1', id='min required password length'),
])
def test_UserCreate_schema(email, password):
    assert UserCreate(email=email, password=password)


@pytest.mark.parametrize(('create_request', 'expected_user_create'), [
    pytest.param(
        {'email': 'valid@email.cft', 'password': 'user_password'},
        UserCreate(email='valid@email.cft', password='user_password'),
        id='valid user to create',
    ),
    pytest.param(
        {'email': 'valid@email.cft', 'password': '1'},
        UserCreate(email='valid@email.cft', password='1'),
        id='min required password length',
    ),
])
def test_UserCreate_schema_json(create_request: dict, expected_user_create):
    assert UserCreate(**create_request) == expected_user_create


@pytest.mark.parametrize(('email', 'password', 'message'), [
    pytest.param(
        None, None,
        'Input should be a valid string',
        id='empty fields'
    ),
    pytest.param(
        'valid@email.cft', None,
        'Input should be a valid string',
        id='empty password'
    ),
    pytest.param(
        'valid@email.cft', '',
        'String should have at least 1 characters',
        id='password is empty string'
    ),
    pytest.param(
        None, 'password',
        'Input should be a valid string',
        id='empty email'
    ),
    pytest.param(
        'not_valid_email.cft', 'password',
        'An email address must have an @-sign',
        id='invalid email without @'
    ),
    pytest.param(
        'not_valid@email', 'password',
        'The part after the @-sign is not valid. It should have a period',
        id='invalid email with @ and without .'
    ),
    pytest.param(
        'not_valid@.cft', 'password',
        'An email address cannot have a period immediately after the @-sign',
        id='invalid email with . after @'
    ),
])
def test_UserCreate_schema_validation_error(email, password, message: str):
    with pytest.raises(ValidationError, match=message):
        assert UserCreate(email=email, password=password)


@pytest.mark.parametrize(('create_request', 'message'), [
    pytest.param(
        {},
        'Field required \[type=missing, input_value=\{\}, input_type=dict\]',
        id='no fields'
    ),
    pytest.param(
        {'email': None, 'password': None},
        'Input should be a valid string',
        id='empty fields'
    ),
    pytest.param(
        {'email': 'valid@email.cft', 'password': None},
        'Input should be a valid string',
        id='empty password'
    ),
    pytest.param(
        {'email': 'valid@email.cft', 'password': ''},
        'String should have at least 1 characters',
        id='password is empty string'
    ),
    pytest.param(
        {'email': None, 'password': 'password'},
        'Input should be a valid string',
        id='empty email'
    ),
    pytest.param(
        {'email': 'not_valid_email.cft', 'password': 'password'},
        'An email address must have an @-sign',
        id='invalid email without @'
    ),
    pytest.param(
        {'email': 'not_valid@email', 'password': 'password'},
        'The part after the @-sign is not valid. It should have a period',
        id='invalid email with @ and without .'
    ),
    pytest.param(
        {'email': 'not_valid@.cft', 'password': 'password'},
        'An email address cannot have a period immediately after the @-sign',
        id='invalid email with . after @'
    ),
])
def test_UserCreate_schema_validation_error_json(create_request: dict, message: str):
    with pytest.raises(ValidationError, match=message):
        assert UserCreate(**create_request)


@pytest.mark.parametrize(('full_name', 'income', 'another_loans', 'birth_date', 'sex'), [
    pytest.param(None, None, None, None, None, id='no fields to update'),
    pytest.param('Новое Полное Имя', None, None, None, Sex.male, id='some fields to update'),
    pytest.param('Новое Полное Имя', 10_000_00, False, datetime.date(1990, 1, 1), Sex.male, id='some fields to update'),
    # по модели валидно, но на сколько корректное поведение?
    pytest.param('    ', None, None, None, None, id='valid full_name with only spaces'),
    pytest.param(None, None, None, datetime.date(2035, 1, 1), None, id='future birth_date'),
])
def test_UserUpdate_schema(full_name, income, another_loans, birth_date, sex):
    assert UserUpdate(
        full_name=full_name,
        income=income,
        another_loans=another_loans,
        birth_date=birth_date,
        sex=sex,
    )


@pytest.mark.parametrize(('update_request', 'expected_user_update'), [
    pytest.param(
        {},
        UserUpdate(full_name=None, income=None, another_loans=None, birth_date=None, sex=None),
        id='no fields to update',
    ),
    pytest.param(
        {'full_name': 'Новое Полное Имя', 'sex': Sex.male},
        UserUpdate(full_name='Новое Полное Имя', income=None, another_loans=None, birth_date=None, sex=Sex.male),
        id='some fields to update',
    ),
    pytest.param(
        {
            'full_name': 'Новое Полное Имя',
            'income': 10_000_00,
            'another_loans': False,
            'birth_date': datetime.date(1990, 1, 1),
            'sex': Sex.female
        },
        UserUpdate(
            full_name='Новое Полное Имя',
            income=10_000_00,
            another_loans=False,
            birth_date=datetime.date(1990, 1, 1),
            sex=Sex.female
        ),
        id='all fields to update'
    ),
    pytest.param(
        {
            'full_name': 'Новое Полное Имя',
            'income': '1000000',
            'another_loans': 'False',
            'birth_date': '1990-01-01',
            'sex': 'male'
        },
        UserUpdate(
            full_name='Новое Полное Имя',
            income=10_000_00,
            another_loans=False,
            birth_date=datetime.date(1990, 1, 1),
            sex=Sex.male
        ),
        id='all fields is str',
    ),
    # по модели валидно, но на сколько корректное поведение?
    pytest.param(
        {'full_name': '     '},
        UserUpdate(full_name='     ', income=None, another_loans=None, birth_date=None, sex=None),
        id='valid full_name with only spaces',

    ),
    pytest.param(
        {'full_name': 'Михайлович'},
        UserUpdate(full_name='Михайлович', income=None, another_loans=None, birth_date=None, sex=None),
        marks=pytest.mark.skip(reason='invalid full_name'),
        id='valid only second name',  # БАГ БР-4.15 ОР: ValidationError ФР: принято

    ),
    # может следует добавить дополнительную валидацию на поле?
    pytest.param(
        {'birth_date': '2035-01-01'},
        UserUpdate(full_name=None, income=None, another_loans=None, birth_date=datetime.date(2035, 1, 1), sex=None),
        id='future birth_date',
    ),
    pytest.param(
        {'hello': 'world'},
        UserUpdate(full_name=None, income=None, another_loans=None, birth_date=None, sex=None),
        id='update request with non existing field',
    ),
])
def test_UserUpdate_schema_json(update_request: dict, expected_user_update):
    assert UserUpdate(**update_request) == expected_user_update


@pytest.mark.parametrize(('full_name', 'income', 'another_loans', 'birth_date', 'sex', 'message'), [
    pytest.param(
        '', None, None, None, None,
        'String should have at least 3 characters',
        id='full_name is empty string',
    ),
    pytest.param(
        'Ян', None, None, None, None,
        'String should have at least 3 characters',
        id='too short full name',
    ),
    pytest.param(
        None, -20, None, None, None,
        'Input should be greater than 0',
        id='less then zero income',
    ),
    pytest.param(
        None, 0, None, None, None,
        'Input should be greater than 0',
        id='zero income',
    ),
])
def test_UserUpdate_schema_validation_error(full_name, income, another_loans, birth_date, sex, message: str):
    with pytest.raises(ValidationError, match=message):
        assert UserUpdate(
            full_name=full_name,
            income=income,
            another_loans=another_loans,
            birth_date=birth_date,
            sex=sex,
        )


@pytest.mark.parametrize(('update_request', 'message'), [
    pytest.param(
        {'full_name': ''},
        'String should have at least 3 characters',
        id='full_name is empty string',
    ),
    pytest.param(
        {'full_name': 'Ян'},
        'String should have at least 3 characters',
        id='too short full name',
    ),
    pytest.param(
        {'income': -20},
        'Input should be greater than 0',
        id='less then zero income',
    ),
    pytest.param(
        {'income': 0},
        'Input should be greater than 0',
        id='zero income',
    ),
    # для более новых версий pydantic кейс бы был без ошибки
    pytest.param(
        {'income': '10_000_00'},
        'Input should be a valid integer, unable to parse string as an integer ',
        id='not valid income str format',
    ),
    pytest.param(
        {'birth_date': '01.01.1990'},
        'Input should be a valid date or datetime, invalid character in year ',
        id='not iso birth_date str format',
    ),
    pytest.param(
        {'birth_date': '01-01'},
        'Input should be a valid date or datetime, input is too short',
        id='birth_date str format without year',
    ),
    pytest.param(
        {'birth_date': '1990-21-01'},
        'Input should be a valid date or datetime, month value is outside expected range of 1-12',
        id='birth_date str format with invalid month',
    ),
    pytest.param(
        {'birth_date': '1990-01-81'},
        'Input should be a valid date or datetime, day value is outside expected range',
        id='birth_date str format with invalid day',
    ),
    pytest.param(
        {'sex': 'N'},
        "Input should be 'male' or 'female'",
        id='not_valid_sex',
    ),
])
def test_UserUpdate_schema_validation_error_json(update_request: dict, message: str):
    with pytest.raises(ValidationError, match=message):
        assert UserUpdate(**update_request)
