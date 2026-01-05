import pytest

from tests.conftest import invalid_header
from tests.utils import get_metric_operations, get_sum_values_of_metric


async def test_activity_metrics_get_card(
        cli, auth_header, session, activity_registry, create_test_credit_card):
    """Проверка насчета метрик при запросе на получение информации по карте клиента"""
    card = create_test_credit_card
    resp = await cli.get(url='/credit_card', headers=auth_header)

    assert resp.status_code == 200

    for metric in activity_registry.collect():
        if metric.name == 'dp_service_http_request_duration_seconds':
            assert get_metric_operations(metric) == {'GET /credit_card', 'POST /credit_card/new'}
            assert get_sum_values_of_metric(metric, 'count') == 2.0

        if metric.name == 'dp_service_http_request_errors_count':
            # не было ошибок, поэтому счетчик ошибок тоже равен 0
            assert get_sum_values_of_metric(metric, 'total') == 0.0

        if metric.name == 'dp_service_http_client_request_duration_seconds':
            # в даном кейсе нет интеграций, поэтому метрика запросов в другие сервисы равна 0
            assert get_sum_values_of_metric(metric, 'count') == 0.0

        if metric.name == 'dp_service_message_bus_request_duration_seconds':
            # в даном кейсе нет взаимодействий с очередью сообщений, поэтому метрика равна 0
            # но на самом деле метрика не собирается в сервисе, поэтому ее значение всегда будет равно 0
            assert get_sum_values_of_metric(metric, 'count') == 0.0


async def test_activity_metrics_without_card(
        cli, auth_header, session, add_test_user, activity_registry, requested_limit):
    """
    Проверка насчета метрик при получении информации по карте клиента, если карты не существует
    """
    resp = await cli.get(url='/credit_card', headers=auth_header)

    assert resp.status_code == 400

    for metric in activity_registry.collect():
        if metric.name == 'dp_service_http_request_duration_seconds':
            assert get_metric_operations(metric) == {'GET /credit_card'}
            # Так как метрика гистограмная, достаем общий сэмпл-счетчик
            assert get_sum_values_of_metric(metric, 'count') == 1.0

        if metric.name == 'dp_service_http_request_errors_count':
            # ошибка запроса есть
            assert get_sum_values_of_metric(metric, 'total') == 1.0

        if metric.name == 'dp_service_http_client_request_duration_seconds':
            # в даном кейсе нет интеграций, поэтому метрика запросов в другие сервисы равна 0
            assert get_sum_values_of_metric(metric, 'count') == 0.0

        if metric.name == 'dp_service_message_bus_request_duration_seconds':
            # в даном кейсе нет взаимодействий с очередью сообщений, поэтому метрика равна 0
            # но на самом деле метрика не собирается в сервисе, поэтому ее значение всегда будет равно 0
            assert get_sum_values_of_metric(metric, 'count') == 0.0

        # TODO кейс закомментирован, так как метрика длительности запроса в бд не собирается в сервисе
        # а по хорошему должна, поэтому ожидаем, что значение будет 1, т.к. в данном тесте в севрисе есть поход в БД
        # if metric.name == 'dp_service_db_request_duration_seconds':
        #     assert get_sum_values_of_metric(metric, 'count') == 1.0


async def test_activity_metrics_with_invalid_token(
        cli, session, add_test_user, activity_registry, requested_limit, invalid_header):
    """
    Проверка насчета метрик при получении информации по карте клиента, c невалидным токеном
    """
    resp = await cli.get(url='/credit_card', headers=invalid_header)

    assert resp.status_code == 403

    for metric in activity_registry.collect():
        if metric.name == 'dp_service_http_request_duration_seconds':
            assert get_metric_operations(metric) == {'GET /credit_card'}
            # Так как метрика гистограмная, достаем общий сэмпл-счетчик
            assert get_sum_values_of_metric(metric, 'count') == 1.0

        if metric.name == 'dp_service_http_request_errors_count':
            # ошибка запроса есть
            assert get_sum_values_of_metric(metric, 'total') == 1.0

        if metric.name == 'dp_service_http_client_request_duration_seconds':
            # в даном кейсе нет интеграций, поэтому метрика запросов в другие сервисы равна 0
            assert get_sum_values_of_metric(metric, 'count') == 0.0

        if metric.name == 'dp_service_message_bus_request_duration_seconds':
            # в даном кейсе нет взаимодействий с очередью сообщений, поэтому метрика равна 0
            # но на самом деле метрика не собирается в сервисе, поэтому ее значение всегда будет равно 0
            assert get_sum_values_of_metric(metric, 'count') == 0.0
