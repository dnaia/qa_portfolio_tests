from tests.utils import get_metric_operations, get_sum_values_of_metric


async def test_activity_metrics_increase_limit_200(
        cli, auth_header, session, requested_limit, add_test_user, activity_registry, add_test_credit_card):
    """Проверка метрик при успешном увеличении лимита кредитной карты"""
    resp = await cli.post(
        url='/credit_card/increase_limit',
        headers=auth_header,
        params={"limit": requested_limit},
    )
    assert resp.status_code == 200

    for metric in activity_registry.collect():
        if metric.name == 'dp_service_http_request_duration_seconds':
            assert get_metric_operations(metric) == {'POST /credit_card/increase_limit'}
            assert get_sum_values_of_metric(metric, 'count') == 1.0

        if metric.name == 'dp_service_http_request_errors_count':
            assert get_sum_values_of_metric(metric, 'total') == 0.0

        if metric.name == 'dp_service_http_client_request_duration_seconds':
            assert get_sum_values_of_metric(metric, 'count') == 0.0

        if metric.name == 'dp_service_message_bus_request_duration_seconds':
            assert get_sum_values_of_metric(metric, 'count') == 0.0

        # TODO: если метрика длительности запроса в БД не собирается, можно xfail
        # if metric.name == 'dp_service_db_request_duration_seconds':
        #     assert get_sum_values_of_metric(metric, 'count') == 1.0


async def test_activity_metrics_increase_limit_without_card_400(
        cli, auth_header, session, requested_limit, add_test_user, activity_registry):
    """Проверка метрик при попытке увеличить лимит, если карты не существует"""
    resp = await cli.post(
        url='/credit_card/increase_limit',
        headers=auth_header,
        params={"limit": requested_limit},
    )
    assert resp.status_code == 400

    for metric in activity_registry.collect():
        if metric.name == 'dp_service_http_request_duration_seconds':
            assert get_metric_operations(metric) == {'POST /credit_card/increase_limit'}
            assert get_sum_values_of_metric(metric, 'count') == 1.0

        if metric.name == 'dp_service_http_request_errors_count':
            assert get_sum_values_of_metric(metric, 'total') == 1.0

        if metric.name == 'dp_service_http_client_request_duration_seconds':
            assert get_sum_values_of_metric(metric, 'count') == 0.0

        if metric.name == 'dp_service_message_bus_request_duration_seconds':
            assert get_sum_values_of_metric(metric, 'count') == 0.0

        # TODO: метрика запроса в БД, если собирается
        # if metric.name == 'dp_service_db_request_duration_seconds':
        #     assert get_sum_values_of_metric(metric, 'count') == 1.0


async def test_activity_metrics_increase_limit_invalid_token_403(
        cli, invalid_header, session, requested_limit, add_test_user, activity_registry):
    """Проверка метрик при увеличении лимита с неверным токеном"""
    resp = await cli.post(
        url='/credit_card/increase_limit',
        headers=invalid_header,
        params={"limit": requested_limit},
    )
    assert resp.status_code == 403

    for metric in activity_registry.collect():
        if metric.name == 'dp_service_http_request_duration_seconds':
            assert get_metric_operations(metric) == {'POST /credit_card/increase_limit'}
            assert get_sum_values_of_metric(metric, 'count') == 1.0

        if metric.name == 'dp_service_http_request_errors_count':
            assert get_sum_values_of_metric(metric, 'total') == 1.0

        if metric.name == 'dp_service_http_client_request_duration_seconds':
            assert get_sum_values_of_metric(metric, 'count') == 0.0

        if metric.name == 'dp_service_message_bus_request_duration_seconds':
            assert get_sum_values_of_metric(metric, 'count') == 0.0


async def test_activity_metrics_increase_limit_user_not_found_404(
        cli, auth_header_deleted_user, requested_limit, activity_registry):
    """Проверка метрик при увеличении лимита для удаленного пользователя"""
    resp = await cli.post(
        url='/credit_card/increase_limit',
        headers=auth_header_deleted_user,
        params={"limit": requested_limit},
    )
    assert resp.status_code == 404

    for metric in activity_registry.collect():
        if metric.name == 'dp_service_http_request_duration_seconds':
            assert get_metric_operations(metric) == {'POST /credit_card/increase_limit'}
            assert get_sum_values_of_metric(metric, 'count') == 1.0

        if metric.name == 'dp_service_http_request_errors_count':
            assert get_sum_values_of_metric(metric, 'total') == 1.0

        if metric.name == 'dp_service_http_client_request_duration_seconds':
            assert get_sum_values_of_metric(metric, 'count') == 0.0

        if metric.name == 'dp_service_message_bus_request_duration_seconds':
            assert get_sum_values_of_metric(metric, 'count') == 0.0
