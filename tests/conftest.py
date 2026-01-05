import asyncio
import datetime
import random
from unittest.mock import MagicMock, AsyncMock

import pytest
from dateutil.relativedelta import relativedelta
from faker import Faker
from httpx import AsyncClient
from sqlalchemy import delete, select

from app.api.errors import *
from app.api.schemas.common import Sex
from app.config import Config, read_config
from app.external.db.models import CreditCardModel, UserModel
from app.service import prepare_app
from app.services.credit_cards import CreditCardService
from app.services.security import SecurityService
from app.system import environment
from app.system.mdw_prometheus_metrics import global_registry
from tests.utils import clear_metrics

fake = Faker(locale='ru-RU')


@pytest.fixture(scope='session')
def config():
    """Базовая конфигурация сервиса в виде pydantic объекта."""
    config = read_config('src/config/config.yml', Config)
    return config


@pytest.fixture(scope='session')
def event_loop():
    """Event loop с измененным scope."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope='session')
def app(config):
    """Возвращает объект приложения FastAPI"""
    environment.initialize(config)
    _app = prepare_app(config)
    return _app


@pytest.fixture(scope='session')
async def cli(app):
    """Возвращает асинхронный клиент приложения"""
    async with AsyncClient(app=app, base_url='http://testserver') as client:
        yield client


@pytest.fixture(scope='session')
def db(app):
    """Фикстура возвращает объект контейнера базы данных приложения"""
    return app.state.container.db()


@pytest.fixture
async def session(db):
    """Фикстура возвращает сессию подключения к БД"""
    async with db.session() as session:
        yield session


@pytest.fixture(scope='session')
def security(app):
    """Фикстура возвращает объект контейнера сервиса безопасности приложения"""
    return app.state.container.security()


@pytest.fixture(scope='session', autouse=True)
async def prepare_db(db):
    """
    Фикстура заполняет БД данными клиентов. Выполняется один раз за прогон.
    После выполнения тестов добавленыые данные удаляются.
    """
    # создаем рандомные данные клиентов
    users = [
        UserModel(
            email=fake.email(),
            hashed_password=fake.password(),
            full_name=fake.name(),
            income=fake.random_int(10_000_00, 50_000_00),
            another_loans=fake.boolean(),
            birth_date=fake.date_of_birth(),
            sex=fake.random_element([Sex.male, Sex.female]),
        ) for _ in range(10)
    ]

    # сохраняем всех клиентов в БД
    async with db.session() as session:
        async with session.begin():
            session.add_all(users)

    # создаем рандомные данные карт для клиентов
    credit_cards = [
        CreditCardModel(
            user_id=user.id,
            limit=10_000_00,
            balance=5_000_00,
            exp_date=fake.date_this_year(),
        ) for user in users
    ]

    # сохраняем все карты в БД
    async with db.session() as session:
        async with session.begin():
            session.add_all(credit_cards)

    yield

    # удаляем все карты и всех клиентов после прогона
    async with db.session() as session:
        async with session.begin():
            for credit_card in credit_cards:
                await session.delete(credit_card)
            for user in users:
                await session.delete(user)


@pytest.fixture
def test_user_email():
    return fake.email()


@pytest.fixture
def test_user_password():
    return fake.password()


@pytest.fixture
async def add_test_user(request, security, session, test_user_email, test_user_password):
    """
    Фикстура добавляет тестового клиента.
    Если необходимо указать определенные параметры клиента, их необходимо передать через словарь с нужными значениями.
    Данные передаются в параметр request через @pytest.mark.fixture_name_data(param_name) перед тестом.

    Поля email и password задаются автоматически.
    По умолчанию будет создан пользователь, который только что зарегистрировался, без дополнительных данных.
    """
    if user_data := request.node.get_closest_marker('add_test_user_data'):
        user_data, = user_data.args

    password = security.get_password_hash(test_user_password)
    if not user_data:
        user = UserModel(email=test_user_email, hashed_password=password)
    else:
        user_data['email'] = test_user_email
        user_data['hashed_password'] = password
        user = UserModel(**user_data)

    session.add(user)
    await session.commit()
    await session.refresh(user)
    # Освобождаем ссылки на экземпляр в текущей сессии
    session.expunge_all()

    yield user
    # СНАЧАЛА удаляем связанные карты
    await session.execute(
        delete(CreditCardModel).where(CreditCardModel.user_id == user.id)
    )

    # ПОТОМ удаляем пользователя
    await session.execute(
        delete(UserModel).where(UserModel.id == user.id)
    )

    await session.commit()


@pytest.fixture
async def add_test_credit_card(security, session, add_test_user):
    """Фикстура добавляет тестовую карту клиента с фиксированными данными"""
    credit_card = CreditCardModel(
        user_id=add_test_user.id,
        limit=10_000_00,
        balance=10_000_00,
        active=True,
        exp_date=datetime.date.today() + relativedelta(years=1)
    )
    session.add(credit_card)
    await session.commit()
    await session.refresh(credit_card)
    # Освобождаем ссылки на экземпляр в текущей сессии
    session.expunge(credit_card)

    yield credit_card

    await session.execute(delete(CreditCardModel).where(CreditCardModel.id == credit_card.id))
    await session.commit()


@pytest.fixture
async def delete_registered_user(test_user_email, session):
    yield
    await session.execute(delete(UserModel).where(UserModel.email == test_user_email))
    await session.commit()


@pytest.fixture
async def auth_header(cli, test_user_password, test_user_email, add_test_user):
    resp = await cli.post('/auth/access_token', data={'username': test_user_email, 'password': test_user_password})
    token = resp.json()['access_token']
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def activity_registry():
    activity_reg = global_registry()._activity_reg
    clear_metrics(activity_reg)
    return activity_reg


@pytest.fixture
def invalid_header():
    """Неверный токен"""
    invalid_header = {"Authorization": "Bearer WRONG.TOKEN.STRING"}
    return invalid_header


@pytest.fixture
async def auth_header_deleted_user(cli, session, security):
    """Токен удаленного пользователя"""
    # 1. создаём пользователя вручную
    email = Faker().email()
    raw_password = "deleted_user_pass"

    user = UserModel(
        email=email,
        hashed_password=security.get_password_hash(raw_password),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    # 2. получаем токен
    resp = await cli.post(
        "/auth/access_token",
        data={"username": email, "password": raw_password},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]

    # 3. удаляем ИМЕННО этого пользователя
    await session.execute(delete(UserModel).where(UserModel.id == user.id))
    await session.commit()

    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def requested_limit():
    """Возвращает случайное значение лимита от 20_000_00 до 500_000_00 включительно."""
    return random.randint(20_000_00, 500_000_00)


@pytest.fixture
async def create_card(cli, auth_header, requested_limit):
    """Создает карту пользователю"""

    async def _create_card(limit=requested_limit, headers=auth_header):
        return await cli.post(
            url="/credit_card/new",
            headers=headers,
            params={"limit": limit},
        )

    return _create_card


@pytest.fixture
async def assert_no_cards(session, add_test_user):
    """Проверка отсутствия карты в БД"""

    async def _assert_no_cards(user_id=None):
        # если user_id не передан — используем тестового пользователя
        if user_id is None:
            user_id = add_test_user.id

        result = await session.execute(
            select(CreditCardModel).where(CreditCardModel.user_id == user_id)
        )
        cards = result.scalars().all()
        assert len(cards) == 0

    return _assert_no_cards


@pytest.fixture
async def assert_no_user(session):
    """Проверка отсутствия пользователя в БД"""

    async def _assert_no_user(user_email: str):
        result = await session.execute(
            select(UserModel).where(UserModel.email == user_email)
        )
        cards = result.scalars().all()
        assert len(cards) == 0

    return _assert_no_user


@pytest.fixture
async def create_test_credit_card(cli, auth_header, session, add_test_user, requested_limit):
    """
    Фикстура создаёт карту через API, берёт её из базы и возвращает объект CreditCardModel.
    """
    # Создаём карту через API
    resp_new = await cli.post(
        url='/credit_card/new',
        headers=auth_header,
        params={"limit": requested_limit},
    )
    assert resp_new.status_code == 200

    # Берём карту из базы
    result = await session.execute(
        select(CreditCardModel).where(CreditCardModel.user_id == add_test_user.id)
    )
    card = result.scalars().first()
    assert card is not None

    return card


@pytest.fixture
def random_user_payload():
    """Генерирует валидный payload пользователя для любых тестов."""

    # доход от 0 до 50 млн
    income = random.randint(300_000_00, 500_000_00)

    # возраст 18–45 лет
    today = datetime.date.today()
    min_birth = today - datetime.timedelta(days=45 * 365)
    max_birth = today - datetime.timedelta(days=18 * 365)
    birth_ts = random.randint(int(min_birth.strftime("%s")), int(max_birth.strftime("%s")))
    birth_date = datetime.date.fromtimestamp(birth_ts).isoformat()

    # случайный пол
    sex = random.choice(["male", "female"])

    # случайное наличие кредитов
    another_loans = random.choice([True, False])

    return {
        "full_name": fake.name(),
        "income": income,
        "another_loans": another_loans,
        "birth_date": birth_date,
        "sex": sex,
    }


@pytest.fixture
async def close_test_credit_card(cli, auth_header, session, add_test_user, requested_limit):
    """
    Закрытие карты пользователя.
    """
    # 1. Создаём карту через /credit_card/new
    resp_new = await cli.post(
        url='/credit_card/new',
        headers=auth_header,
        params={"limit": requested_limit},
    )
    assert resp_new.status_code == 200

    # 2. Закрываем карту через /credit_card/close
    resp_close = await cli.post(
        url='/credit_card/close',
        headers=auth_header,
    )
    assert resp_close.status_code == 200
    assert resp_close.json().get("detail") == "closed"

    # 3. Берём карту из базы и убеждаемся, что она закрыта
    result = await session.execute(
        select(CreditCardModel).where(CreditCardModel.user_id == add_test_user.id)
    )
    card = result.scalars().first()
    assert card is not None
    assert card.active is False

    return card


@pytest.fixture(params=[
    CredentialsError,
    TokenError,
    UserNotFoundError,
    CreditCardAlreadyExistError,
    CreditCardNotExistError,
    CreditCardNotActiveError,
    CreditCardSmallLimitError,
    CreditCardCantIncreaseLimitError,
    UserAlreadyExistError,
])
def error_class(request):
    """Фикстура, возвращающая класс ошибки."""
    return request.param


@pytest.fixture
def error_instance(error_class):
    """Фикстура, возвращающая экземпляр ошибки."""
    return error_class()


@pytest.fixture
def credit_card_mock():
    mock = MagicMock()

    # мок контекстного менеджера
    session_context = MagicMock()
    session_context.begin = AsyncMock()
    session_context.add = MagicMock()
    session_context.refresh = AsyncMock()

    # session_factory() →
    mock.session_factory.return_value.__aenter__.return_value = session_context

    # дата карты
    mock.exp_date = datetime.date.today()

    return mock