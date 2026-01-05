import datetime
from unittest.mock import MagicMock, AsyncMock

import pytest
from dateutil.relativedelta import relativedelta
from fastapi.encoders import jsonable_encoder
from sqlalchemy import delete, select

from app.api.schemas.common import Sex
from app.api.schemas.user import UserCreate, UserUpdate
from app.external.db.models import UserModel
from app.services.credit_cards import CreditCardService
from app.services.users import UserService


@pytest.fixture
def credit_card_mock():
    session = MagicMock()
    session.begin.return_value.__aenter__ = AsyncMock(return_value=None)
    session.begin.return_value.__aexit__ = AsyncMock(return_value=None)
    session.add = MagicMock()
    session.refresh = AsyncMock()

    session_factory = MagicMock()
    session_factory.return_value.__aenter__ = AsyncMock(return_value=session)
    session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    return CreditCardService(
        session_factory=session_factory,
        exp_date_in_years=5,
        default_limit=20_000_00,
    )


@pytest.fixture
def user_service_mock():
    """Мок сервиса UserService с поддельной session_factory."""
    session = MagicMock()
    session.begin.return_value.__aenter__ = AsyncMock(return_value=None)
    session.begin.return_value.__aexit__ = AsyncMock(return_value=None)
    session.add = MagicMock()
    session.scalar = AsyncMock()

    session_factory = MagicMock()
    session_factory.return_value.__aenter__ = AsyncMock(return_value=session)
    session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    security = MagicMock()
    security.get_password_hash.return_value = "HASH"
    security.verify_password.return_value = True

    service = UserService(
        session_factory=session_factory,
        security_service=security,
    )

    # прикладываем session, чтобы можно было проверять вызовы
    service._mock_session = session
    return service


@pytest.fixture
async def email(session, request):
    yield request.param
    await session.execute(delete(UserModel).where(UserModel.email == request.param))
    await session.commit()


# indirect позволяет передать в фикстуру email значение параметра
@pytest.mark.parametrize('email', ['test@user.email'], indirect=['email'])
async def test_add_valid_user(
        user_service,
        session,
        email,
):
    expected_user = UserModel(email=email)
    user_in = UserCreate(email=email, password='test_user_password')

    added_user = await user_service.add(user_in=user_in)

    assert added_user.email == expected_user.email

    user_in_db = await session.scalar(select(UserModel).where(UserModel.email == email))
    assert user_in_db.email == expected_user.email
    assert user_in_db.hashed_password == added_user.hashed_password


@pytest.mark.parametrize('user_in', [
    pytest.param(
        UserUpdate(
            full_name='Hello Im User',
            income=10_000_00,
            another_loans=False,
            birth_date=datetime.date.today() - relativedelta(years=25),
            sex=Sex.male,
        ),
        id='fill all data to new user with empty data'
    ),
    pytest.param(
        UserUpdate(
            full_name='Hello Im User',
            income=10_000_00,
            another_loans=False,
            birth_date=datetime.date.today() - relativedelta(years=25),
            sex=Sex.male,
        ),
        marks=pytest.mark.add_test_user_data({
            'full_name': 'Some Big Name',
            'income': 500_00,
            'another_loans': True,
            'birth_date': datetime.date.today() - relativedelta(years=21),
            'sex': Sex.female,
        }),
        id='update all data to user with data',
    ),
    pytest.param(
        UserUpdate(
            full_name=None,  # заполненный параметр на None
            birth_date=datetime.date.today() - relativedelta(years=25),  # заполненный параметр на другое значние
            sex=Sex.male,  # None на другое значение
        ),
        marks=pytest.mark.add_test_user_data({
            'full_name': 'Some Big Name',
            'income': 500_00,
            'another_loans': True,
            'birth_date': datetime.date.today() - relativedelta(years=21),
            'sex': None,
        }),
        id='update some params to user with data',
    ),
    pytest.param(
        UserUpdate(),
        marks=pytest.mark.add_test_user_data({
            'full_name': 'Some Big Name',
            'income': 500_00,
            'another_loans': True,
            'birth_date': datetime.date.today() - relativedelta(years=21),
            'sex': None,
        }),
        id='no fields to update',
    ),
    pytest.param(
        UserUpdate(
            income=1,  # изменили на меньшее значение
            another_loans=True,
            sex="female",
        ),
        marks=pytest.mark.add_test_user_data({
            'full_name': 'Some Big Name',
            'income': 500_00,
            'another_loans': None,
            'birth_date': datetime.date.today() - relativedelta(years=21),
            'sex': None,
        }),
        id='update income to decrease',
    ),
    pytest.param(
        UserUpdate(
            full_name='Mikhailovich',
        ),
        marks=pytest.mark.add_test_user_data({
            'full_name': None,
            'income': 500_00,
            'another_loans': True,
            'birth_date': datetime.date.today() - relativedelta(years=21),
            'sex': None,
        }),
        id='update_patronymic_name',
    )
])
async def test_update_user(
        user_service,
        add_test_user,
        session,
        user_in: UserUpdate,
):
    await user_service.update(user_in=user_in, user_db=add_test_user)

    updated_user = await session.scalar(select(UserModel).where(UserModel.email == add_test_user.email))
    user_in_data = user_in.model_dump(exclude_unset=True)
    updated_user_data = jsonable_encoder(updated_user)

    for field in updated_user_data:
        # если в UserUpdate задан параметр, то проверяем, что в обновленной записи он изменился
        if field in user_in_data:
            assert getattr(updated_user, field) == getattr(user_in, field)
        # иначе, проверяем, что параметр остался без изменений
        else:
            assert getattr(updated_user, field) == getattr(add_test_user, field)


async def test_get_by_email_found(user_service, mock_session_factory):
    session = mock_session_factory()
    expected_user = UserModel(email="x@mail.com")
    session.scalar.return_value = expected_user

    result = await user_service.get_by_email("x@mail.com")

    assert result == expected_user
    session.scalar.assert_called_once()


async def test_get_by_email_found(user_service_mock):
    """Возвращает пользователя, если session.scalar вернул UserModel."""
    expected = UserModel(email="test@mail.com")

    user_service_mock._mock_session.scalar.return_value = expected

    result = await user_service_mock.get_by_email("test@mail.com")

    assert result == expected
    user_service_mock._mock_session.scalar.assert_called_once()


async def test_get_by_email_not_found(user_service_mock):
    """Возвращает None, если пользователь не найден."""
    user_service_mock._mock_session.scalar.return_value = None

    result = await user_service_mock.get_by_email("no@mail.com")

    assert result is None


async def test_add_user(user_service_mock):
    """Создание пользователя — проверяем пароль и сохранение."""
    user_in = UserCreate(email="a@b.c", password="pass123")

    result = await user_service_mock.add(user_in)

    assert result.email == "a@b.c"
    assert result.hashed_password == "HASH"  # подделка в фикстуре

    session = user_service_mock._mock_session
    session.add.assert_called_once()


async def test_authenticate_success(user_service_mock):
    """Успешная аутентификация."""
    user = UserModel(email="a@b.c", hashed_password="HASH")
    user_service_mock._mock_session.scalar.return_value = user

    result = await user_service_mock.authenticate("a@b.c", "pass123")

    assert result == user
    user_service_mock.security_service.verify_password.assert_called_once()


async def test_authenticate_no_user(user_service_mock):
    """Если пользователь не найден — вернуть None."""
    user_service_mock._mock_session.scalar.return_value = None

    result = await user_service_mock.authenticate("a@b.c", "pass")

    assert result is None


async def test_authenticate_wrong_password(user_service_mock):
    """Неверный пароль → None."""
    user = UserModel(email="a@b.c", hashed_password="HASH")
    user_service_mock._mock_session.scalar.return_value = user
    user_service_mock.security_service.verify_password.return_value = False

    result = await user_service_mock.authenticate("a@b.c", "BAD")

    assert result is None


async def test_update_user(user_service_mock):
    """Обновление данных пользователя — только изменённые поля."""
    user = UserModel(full_name="OLD", income=10)
    update = UserUpdate(full_name="NEW")

    await user_service_mock.update(update, user)

    assert user.full_name == "NEW"
    assert user.income == 10  # не изменено

    session = user_service_mock._mock_session
    session.add.assert_called_once_with(user)


async def test_update_status_doc(user_service_mock):
    """update_status_doc — изменяет поле status_document."""
    user = UserModel(status_document=False)

    await user_service_mock.update_status_doc(user_db=user, status=True)

    assert user.status_document is True
    user_service_mock._mock_session.add.assert_called_once_with(user)


async def test_update_status_face(user_service_mock):
    """update_status_face — изменяет поле status_face."""
    user = UserModel(status_face=False)

    await user_service_mock.update_status_face(user_db=user, status=True)

    assert user.status_face is True
    user_service_mock._mock_session.add.assert_called_once_with(user)
