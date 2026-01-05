import pytest
from fastapi import FastAPI

from app.api.routes import setup_routes
from app.system.mdw_fastapi.api.route import LoggedRoute


@pytest.fixture
def app():
    return FastAPI()


def test_setup_routes_registers_healthz_endpoints(app):
    setup_routes(app)

    paths = {route.path for route in app.routes}

    assert "/healthz/up" in paths
    assert "/healthz/ready" in paths
    assert "/healthz/metrics" in paths


def test_setup_routes_registers_auth_endpoints(app):
    setup_routes(app)

    paths = {route.path for route in app.routes}
    assert "/auth/access_token" in paths


def test_setup_routes_registers_user_endpoints(app):
    setup_routes(app)

    paths = {route.path for route in app.routes}

    assert "/user" in paths  # GET
    assert "/user/register" in paths  # POST
    assert "/user/document" in paths  # POST
    assert "/user/face" in paths  # POST


def test_setup_routes_registers_credit_card_endpoints(app):
    setup_routes(app)

    paths = {route.path for route in app.routes}

    assert "/credit_card" in paths
    assert "/credit_card/new" in paths
    assert "/credit_card/increase_limit" in paths
    assert "/credit_card/close" in paths
