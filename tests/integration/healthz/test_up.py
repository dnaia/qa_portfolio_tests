async def test_up(cli):
    resp = await cli.get('/healthz/up')
    assert resp.status_code == 200
