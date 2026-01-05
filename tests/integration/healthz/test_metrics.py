async def test_metrics_activity(cli):
    resp = await cli.get('/healthz/metrics?type=activity')
    assert resp.status_code == 200


async def test_metrics_health(cli):
    resp = await cli.get('/healthz/metrics?type=health')
    assert resp.status_code == 200


async def test_metrics_analytics(cli):
    resp = await cli.get('/healthz/metrics?type=analytics')
    assert resp.status_code == 200


async def test_delete_metrics_all(cli):
    resp = await cli.delete("/healthz/metrics")
    assert resp.status_code == 200


async def test_delete_metrics_health(cli):
    resp = await cli.delete("/healthz/metrics?type=health")
    assert resp.status_code == 200


async def test_delete_metrics_activity(cli):
    resp = await cli.delete("/healthz/metrics?type=activity")
    assert resp.status_code == 200


async def test_metrics_incorrect(cli):
    resp = await cli.get('/healthz/metrics?type=unknown')
    assert resp.status_code == 422


async def test_delete_metrics_incorrect(cli):
    resp = await cli.delete('/healthz/metrics?type=unknown')
    assert resp.status_code == 422
