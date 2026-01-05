import pytest

from tests.utils import get_metric_operations, get_sum_values_of_metric


async def test_activity_metrics_close(
        cli,
        auth_header,
        add_test_credit_card,
        activity_registry,
):
    """Проверка насчета метрик при закрытии карты клиента"""
    resp = await cli.post(url='/credit_card/close', headers=auth_header)

    assert resp.status_code == 200

    for metric in activity_registry.collect():
        if metric.name == 'dp_service_http_request_duration_seconds':
            ops = get_metric_operations(metric)
            assert 'POST /credit_card/close' in ops
            assert get_sum_values_of_metric(metric, 'count') >= 1

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
async def test_db_request_duration_metric_close(
        cli,
        auth_header,
        add_test_credit_card,
        activity_registry,
):
    """Проверка насчета метрики dp_service_db_request_duration_seconds при закрытии карты клиента"""
    resp = await cli.post(url='/credit_card/close', headers=auth_header)

    assert resp.status_code == 200

    for metric in activity_registry.collect():
        if metric.name == 'dp_service_db_request_duration_seconds':
            assert get_sum_values_of_metric(metric, 'count') == 1.0


async def test_activity_metrics_close_non_existent_card(
        cli,
        auth_header,
        activity_registry,
):
    """
    Проверка насчета метрик при закрытии карты клиента, если карты не существует
    """
    resp = await cli.post(url='/credit_card/close', headers=auth_header)

    assert resp.status_code == 400

    for metric in activity_registry.collect():
        if metric.name == 'dp_service_http_request_duration_seconds':
            ops = get_metric_operations(metric)
            assert 'POST /credit_card/close' in ops
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
