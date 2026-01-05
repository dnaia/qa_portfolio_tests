import os
import tempfile
from unittest.mock import AsyncMock

import pytest

from app.services.photo import ClientSession, PhotoService


@pytest.fixture()
def face_photo():
    # создаём временный файл
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpeg")

    try:
        # записываем в него 5 мегабайт данных
        tmp.write(os.urandom(5 * 1024 * 1024))  # 5 МБ
        tmp.flush()

        # открываем как файл для тестов
        with open(tmp.name, "rb") as f:
            yield f
    finally:
        # удаляем после теста
        os.unlink(tmp.name)


@pytest.fixture()
async def photo_service_post_request_mock(monkeypatch):
    """Мок POST запроса в cервис для валидации фотографий."""

    class PhotoServiceResponseMock:
        """Класс, имитирующий ответ cервиса для валидации фотографий."""

        def __init__(self, status, resp):
            self.status = status
            self.resp = resp

        async def json(self):
            return {'status': self.resp}

    with monkeypatch.context() as m:
        async def post_request_mock(*args, **kwargs):
            post_mock_response = PhotoServiceResponseMock(m.status, m.response_body)

            return post_mock_response

        m.status = 200
        m.response_body = 'OK'

        m.setattr(ClientSession, 'post', post_request_mock)
        yield m


@pytest.mark.parametrize(
    ('photo_service_response', 'expected_code', 'expected_response'),
    [
        ('OK', 200, 'validated'),
        ('NOT OK', 400, 'not validated')
    ]
)
async def test_photo_service_handler(
        photo_service_response,
        expected_code,
        expected_response,
        auth_header,
        cli,
        face_photo,
        photo_service_post_request_mock,
):
    """Проверка запроса на валидацию фото, мокаем ответ cервиса для валидации фотографий."""

    files = {'file': ('image.jpeg', face_photo)}
    photo_service_post_request_mock.response_body = photo_service_response

    resp = await cli.post('/user/face', headers=auth_header, files=files)

    assert resp.status_code == expected_code
    assert resp.json()['detail'] == expected_response


async def test_di(app, cli, auth_header, face_photo):
    """Проверка запроса на валидацию документа, мокаем зависимость PhotoService через DI"""
    files = {'file': ('image.jpeg', face_photo)}

    service_photo_mock = AsyncMock(spec=PhotoService)
    service_photo_mock.validate_photo.return_value = True

    with app.state.container.photo_service.override(service_photo_mock):
        resp = await cli.post('/user/face', headers=auth_header, files=files)

        assert resp.status_code == 200
        assert resp.json()['detail'] == 'validated'
        assert service_photo_mock.validate_photo.call_args.kwargs['photo_type'] == 'face'
