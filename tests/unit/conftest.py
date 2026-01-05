from unittest.mock import AsyncMock, MagicMock
import pytest

from app.services.credit_cards import CreditCardService
from app.services.security import SecurityService
from app.services.users import UserService


@pytest.fixture(scope='session')
def credit_card_service(config, db):
    return CreditCardService(
        session_factory=db.session,
        exp_date_in_years=config.credit_card.exp_date_in_years,
        default_limit=config.credit_card.default_limit,
    )


@pytest.fixture(scope='session')
def security_service(config):
    return SecurityService(
        secret_key=config.jwt.secret,
        token_ttl=config.jwt.access_token_expire_minutes,
    )


@pytest.fixture(scope='session')
def user_service(config, security_service, db):
    return UserService(
        session_factory=db.session,
        security_service=security_service,
    )
