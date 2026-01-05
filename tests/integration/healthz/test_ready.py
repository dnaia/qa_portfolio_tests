from http import HTTPStatus

import pytest


async def test_ready(cli):
    resp = await cli.get('/healthz/ready')
    assert resp.status_code == 200


@pytest.mark.xfail(reason="503 сервис недоступен",
                   raises=AssertionError)  # БР - 12.3; ОР: 503, ФР: 500
async def test_healthz_ready_503_when_db_down(cli, app, monkeypatch, db):
    """Проверяем, что при недоступной БД /healthz/ready возвращает 503."""

    db = app.state.container.db()

    # Mock: база недоступна
    monkeypatch.setattr(db, "is_connected", lambda: False)

    resp = await cli.get("/healthz/ready")

    assert resp.status_code == HTTPStatus.SERVICE_UNAVAILABLE
