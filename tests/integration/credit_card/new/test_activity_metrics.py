import pytest

from tests.conftest import auth_header, auth_header_deleted_user
from tests.utils import get_metric_operations, get_sum_values_of_metric


async def test_activity_metrics_new_card_200(
        cli, auth_header, session, requested_limit, add_test_user, activity_registry):
    """Проверка насчета метрик при открытии карты клиента"""
    resp = await cli.post(url='/credit_card/new', headers=auth_header, params={"limit": requested_limit})

    assert resp.status_code == 200

    for metric in activity_registry.collect():
        if metric.name == 'dp_service_http_request_duration_seconds':
            ops = get_metric_operations(metric)
            assert 'POST /credit_card/new' in ops
            assert get_sum_values_of_metric(metric, 'count') == 1.0

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


@pytest.mark.xfail(reason='Метрика длительности запроса в бд не собирается в сервисе', raises=AssertionError)
async def test_db_request_duration_metric_new(
        cli,
        auth_header,
        add_test_credit_card,
        activity_registry,
):
    """Проверка насчета метрики dp_service_db_request_duration_seconds при открытии карты клиента"""
    resp = await cli.post(url='/credit_card/new', headers=auth_header)

    assert resp.status_code == 200

    for metric in activity_registry.collect():
        if metric.name == 'dp_service_db_request_duration_seconds':
            assert get_sum_values_of_metric(metric, 'count') == 1.0


async def test_activity_metrics_new_second_card_400(
        cli, auth_header, session, add_test_user, activity_registry, requested_limit):
    """
    Проверка насчета метрик при закрытии карты клиента, если карты не существует
    """
    resp_1 = await cli.post(url='/credit_card/new', headers=auth_header, params={"limit": requested_limit})
    resp_2 = await cli.post(url='/credit_card/new', headers=auth_header, params={"limit": requested_limit})

    assert resp_2.status_code == 400

    for metric in activity_registry.collect():
        if metric.name == 'dp_service_http_request_duration_seconds':
            ops = get_metric_operations(metric)
            assert 'POST /credit_card/new' in ops
            # Так как метрика гистограмная, достаем общий сэмпл-счетчик
            assert get_sum_values_of_metric(metric, 'count') == 2.0

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


async def test_activity_metrics_with_invalid_token_403(
        cli, session, requested_limit, add_test_user, activity_registry, invalid_header):
    """Проверка насчета метрик при открытии карты клиента"""
    resp = await cli.post(url='/credit_card/new', headers=invalid_header, params={"limit": requested_limit})

    assert resp.status_code == 403

    for metric in activity_registry.collect():
        if metric.name == 'dp_service_http_request_duration_seconds':
            ops = get_metric_operations(metric)
            assert 'POST /credit_card/new' in ops
            assert get_sum_values_of_metric(metric, 'count') == 1.0

        if metric.name == 'dp_service_http_request_errors_count':
            # не было ошибок, поэтому счетчик ошибок тоже равен 0
            assert get_sum_values_of_metric(metric, 'total') == 1.0

        if metric.name == 'dp_service_http_client_request_duration_seconds':
            # в даном кейсе нет интеграций, поэтому метрика запросов в другие сервисы равна 0
            assert get_sum_values_of_metric(metric, 'count') == 0.0

        if metric.name == 'dp_service_message_bus_request_duration_seconds':
            # в даном кейсе нет взаимодействий с очередью сообщений, поэтому метрика равна 0
            # но на самом деле метрика не собирается в сервисе, поэтому ее значение всегда будет равно 0
            assert get_sum_values_of_metric(metric, 'count') == 0.0


async def test_activity_metrics_ew_card_user_not_found_404(
        cli, session, requested_limit, activity_registry, auth_header_deleted_user):
    """Проверка насчета метрик при открытии карты клиента"""
    resp = await cli.post(url='/credit_card/new', headers=auth_header_deleted_user, params={"limit": requested_limit})

    assert resp.status_code == 404

    for metric in activity_registry.collect():
        if metric.name == 'dp_service_http_request_duration_seconds':
            assert get_metric_operations(metric) == {'POST /credit_card/new', 'POST /auth/access_token'}
            assert get_sum_values_of_metric(metric, 'count') == 2.0

        if metric.name == 'dp_service_http_request_errors_count':
            # не было ошибок, поэтому счетчик ошибок тоже равен 0
            assert get_sum_values_of_metric(metric, 'total') == 1.0

        if metric.name == 'dp_service_http_client_request_duration_seconds':
            # в даном кейсе нет интеграций, поэтому метрика запросов в другие сервисы равна 0
            assert get_sum_values_of_metric(metric, 'count') == 0.0

        if metric.name == 'dp_service_message_bus_request_duration_seconds':
            # в даном кейсе нет взаимодействий с очередью сообщений, поэтому метрика равна 0
            # но на самом деле метрика не собирается в сервисе, поэтому ее значение всегда будет равно 0
            assert get_sum_values_of_metric(metric, 'count') == 0.0


async def test_activity_metrics_with_invalid_limit_422(
        cli, auth_header, session, requested_limit, add_test_user, activity_registry):
    """Проверка насчета метрик при открытии карты клиента"""
    resp = await cli.post(url='/credit_card/new', headers=auth_header, params={"limit": "тридцать тысяч"})

    assert resp.status_code == 422

    for metric in activity_registry.collect():
        if metric.name == 'dp_service_http_request_duration_seconds':
            ops = get_metric_operations(metric)
            assert 'POST /credit_card/new' in ops
            assert get_sum_values_of_metric(metric, 'count') == 1.0

        if metric.name == 'dp_service_http_request_errors_count':
            # не было ошибок, поэтому счетчик ошибок тоже равен 0
            assert get_sum_values_of_metric(metric, 'total') == 1.0

        if metric.name == 'dp_service_http_client_request_duration_seconds':
            # в даном кейсе нет интеграций, поэтому метрика запросов в другие сервисы равна 0
            assert get_sum_values_of_metric(metric, 'count') == 0.0

        if metric.name == 'dp_service_message_bus_request_duration_seconds':
            # в даном кейсе нет взаимодействий с очередью сообщений, поэтому метрика равна 0
            # но на самом деле метрика не собирается в сервисе, поэтому ее значение всегда будет равно 0
            assert get_sum_values_of_metric(metric, 'count') == 0.0
