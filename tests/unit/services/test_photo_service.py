import logging
from asyncio import TimeoutError
from unittest.mock import AsyncMock

import pytest
from aiohttp import ClientResponseError

from app.external.http_errors import HttpClientTimeoutError, HttpClientError
from app.services.photo import PhotoService, PhotoServiceConfig


@pytest.fixture
def image_mock():
    """Мок файла для отправки в PhotoService."""
    image = AsyncMock()
    image.read.return_value = b'photo_content'
    image.content_type = 'image/jpeg'
    image.filename = 'photo.jpg'

    return image


@pytest.fixture
def mock_session():
    """Мок с подделанными post/get методами."""
    session = AsyncMock()
    session.post = AsyncMock()
    session.get = AsyncMock()
    return session


@pytest.fixture
def photo_service_config(config):
    """Базовая конфигурация объекта PhotoService."""
    return PhotoServiceConfig(
        url=config.photo_service.url,
        timeout=config.photo_service.timeout
    )


async def test_photo_service_timeout_error(photo_service_config, image_mock, caplog):
    """Проверка поведения при TimeoutError запросов к сервису валидации фотографий."""

    photo_service_session = AsyncMock()
    photo_service_session.post.side_effect = TimeoutError

    photo_service = PhotoService(photo_service_session, photo_service_config)

    with pytest.raises(HttpClientTimeoutError):
        await photo_service.validate_photo(image_mock, 'doc')

    assert f'PhotoService unavailable by {photo_service._request_timeout} secs timeout.' in caplog.messages


async def test_validate_photo_ok(mock_session, photo_service_config, image_mock):
    """Возврат True при статусе 200 и ответе {'status': 'OK'}."""
    mock_session.post.return_value.status = 200
    mock_session.post.return_value.json = AsyncMock(return_value={"status": "OK"})

    service = PhotoService(mock_session, photo_service_config)

    result = await service.validate_photo(image_mock, "face")

    assert result is True


async def test_validate_photo_not_ok(mock_session, photo_service_config, image_mock):
    """Возврат False при статусе 200, но ответе != OK."""
    mock_session.post.return_value.status = 200
    mock_session.post.return_value.json = AsyncMock(return_value={"status": "FAIL"})

    service = PhotoService(mock_session, photo_service_config)

    result = await service.validate_photo(image_mock, "face")

    assert result is False


async def test_validate_photo_bad_status(mock_session, photo_service_config, image_mock):
    """Проверяет: если PhotoService возвращает статус != 200 — выбрасывается HttpClientError."""
    mock_session.post.return_value.status = 500
    mock_session.post.return_value.text = AsyncMock(return_value="server error")

    service = PhotoService(mock_session, photo_service_config)

    with pytest.raises(HttpClientError):
        await service.validate_photo(image_mock, "face")


async def test_validate_photo_doc_endpoint(mock_session, photo_service_config, image_mock):
    """Выбор endpoint /doc при photo_type='doc'."""
    mock_session.post.return_value.status = 200
    mock_session.post.return_value.json = AsyncMock(return_value={"status": "OK"})

    service = PhotoService(mock_session, photo_service_config)

    await service.validate_photo(image_mock, "doc")

    url_called = mock_session.post.call_args[0][0]
    assert url_called.path.endswith("/doc")


async def test_validate_photo_face_endpoint(mock_session, photo_service_config, image_mock):
    """Выбор endpoint /face при photo_type='face'."""
    mock_session.post.return_value.status = 200
    mock_session.post.return_value.json = AsyncMock(return_value={"status": "OK"})

    service = PhotoService(mock_session, photo_service_config)

    await service.validate_photo(image_mock, "face")

    url_called = mock_session.post.call_args[0][0]
    assert url_called.path.endswith("/face")


async def test_is_connected_true(mock_session, photo_service_config):
    """is_connected возвращает True при status 200."""
    mock_session.get.return_value.status = 200
    service = PhotoService(mock_session, photo_service_config)

    assert await service.is_connected() is True


@pytest.mark.asyncio
async def test_is_connected_false(mock_session, photo_service_config):
    """is_connected возвращает False при status != 200."""
    mock_session.get.return_value.status = 500
    service = PhotoService(mock_session, photo_service_config)

    assert await service.is_connected() is False


async def test_validate_photo_calls_photo_read(mock_session, photo_service_config, image_mock):
    """Проверяет, что фото читается при формировании FormData."""
    mock_session.post.return_value.status = 200
    mock_session.post.return_value.json = AsyncMock(return_value={"status": "OK"})

    service = PhotoService(mock_session, photo_service_config)

    await service.validate_photo(image_mock, "face")

    image_mock.read.assert_called_once()


async def test_validate_photo_logs_response(mock_session, photo_service_config, image_mock, caplog):
    """Проверяем, что логируется успешный ответ."""
    mock_session.post.return_value.status = 200
    mock_session.post.return_value.json = AsyncMock(return_value={"status": "OK"})

    service = PhotoService(mock_session, photo_service_config)

    with caplog.at_level(logging.INFO):
        await service.validate_photo(image_mock, "face")

    assert "PhotoService response" in caplog.text
