from copy import deepcopy
import json
import math

import pytest
import requests

from services import sales_tax as sales
from utils.geography import ABBR_TO_NAME


@pytest.fixture(autouse=True)
def reset_cache():
    sales._cache.clear()
    sales._requests.clear()
    sales._blocked_until = 0
    yield
    sales._cache.clear()
    sales._requests.clear()
    sales._blocked_until = 0


def payload(zip_code='23220', state='VA'):
    return {'success': True, 'data': {'zip_code': zip_code, 'state': state,
            'last_updated': '2026-01-20T13:36:39.000Z',
            'rates': {'combined': .06, 'state': .043, 'county': .01, 'city': 0, 'local': .007}}}


class Response:
    def __init__(self, data=None, status=200):
        self.data = data
        self.status_code = status

    def json(self):
        return deepcopy(self.data)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError()


def test_snapshot_complete_and_independent_of_network(monkeypatch):
    monkeypatch.setattr(sales.requests, 'get', lambda *a, **k: pytest.fail('State view called network'))
    df = sales.state_sales_taxes()
    assert set(df.abbr) == set(ABBR_TO_NAME)
    assert len(df) == 51
    assert df.abbr.is_unique
    assert all(abs(r.sales_state_rate + r.sales_local_average - r.sales_combined_average) <= .02 for r in df.itertuples())
    # Preserve the published negative NJ average (reduced-rate zones).
    assert df.set_index('abbr').loc['NJ', 'sales_local_average'] < 0
    assert df.set_index('abbr').loc['OR', 'sales_combined_average'] == 0


def test_lookup_cached_and_caller_cannot_mutate_cache(monkeypatch):
    calls = []
    def get(url, **kwargs):
        calls.append(url)
        assert kwargs['timeout'] == (3, 5)
        return Response(payload())
    monkeypatch.setattr(sales.requests, 'get', get)
    first = sales.lookup_zip('23220')
    assert first['rates']['combined'] == .06
    first['rates']['combined'] = .99
    assert sales.lookup_zip('23220')['rates']['combined'] == .06
    assert len(calls) == 1


@pytest.mark.parametrize('zip_code', ['', '1234', '123456', '12abc', '../foo', '１２３４５'])
def test_invalid_zip_never_calls_provider(monkeypatch, zip_code):
    monkeypatch.setattr(sales.requests, 'get', lambda *a, **k: pytest.fail('Invalid ZIP called network'))
    with pytest.raises(sales.SalesTaxError):
        sales.lookup_zip(zip_code)


def test_leading_zero_preserved(monkeypatch):
    monkeypatch.setattr(sales.requests, 'get', lambda url, **k: Response(payload('02108', 'MA')))
    assert sales.lookup_zip('02108')['zip_code'] == '02108'


@pytest.mark.parametrize('change', ['sum', 'nan', 'negative', 'missing', 'zip', 'state', 'date', 'future', 'boolean'])
def test_rejects_invalid_provider_data(monkeypatch, change):
    p = payload()
    if change == 'sum': p['data']['rates']['local'] = .04875
    if change == 'nan': p['data']['rates']['combined'] = math.nan
    if change == 'negative': p['data']['rates']['county'] = -.01
    if change == 'missing': del p['data']['rates']['county']
    if change == 'zip': p['data']['zip_code'] = '10001'
    if change == 'state': p['data']['state'] = 'XX'
    if change == 'date': p['data']['last_updated'] = 'yesterday'
    if change == 'future': p['data']['last_updated'] = '2999-01-01T00:00:00Z'
    if change == 'boolean': p['data']['rates']['city'] = False
    monkeypatch.setattr(sales.requests, 'get', lambda *a, **k: Response(p))
    with pytest.raises(sales.SalesTaxError):
        sales.lookup_zip('23220')
    assert '23220' not in sales._cache


def test_real_inconsistent_new_york_response_is_rejected(monkeypatch):
    p = payload('10001', 'NY')
    p['data']['rates'] = dict(combined=.08875, state=.04, county=0, city=.045, local=.04875)
    monkeypatch.setattr(sales.requests, 'get', lambda *a, **k: Response(p))
    with pytest.raises(sales.SalesTaxError, match='inconsistent'):
        sales.lookup_zip('10001')


def test_zero_tax_is_not_missing(monkeypatch):
    p = payload('99501', 'AK')
    p['data']['rates'] = {k: 0 for k in p['data']['rates']}
    monkeypatch.setattr(sales.requests, 'get', lambda *a, **k: Response(p))
    assert sales.lookup_zip('99501')['rates']['combined'] == 0


@pytest.mark.parametrize('status', [404, 429, 500])
def test_http_failures_leave_snapshot_available(monkeypatch, status):
    monkeypatch.setattr(sales.requests, 'get', lambda *a, **k: Response(status=status))
    with pytest.raises(sales.SalesTaxError):
        sales.lookup_zip('00000')
    assert len(sales.state_sales_taxes()) == 51


def test_timeout_backoff_and_expired_cache_fallback(monkeypatch):
    monkeypatch.setattr(sales.requests, 'get', lambda *a, **k: Response(payload()))
    sales.lookup_zip('23220')
    stamp, quote = sales._cache['23220']
    sales._cache['23220'] = (stamp - sales.CACHE_SECONDS - 1, quote)
    calls = []
    def timeout(*a, **k):
        calls.append(1)
        raise requests.Timeout()
    monkeypatch.setattr(sales.requests, 'get', timeout)
    assert sales.lookup_zip('23220')['stale'] is True
    with pytest.raises(sales.SalesTaxError):
        sales.lookup_zip('99501')
    assert len(calls) == 1


def test_malformed_json_is_handled(monkeypatch):
    class Bad(Response):
        def json(self):
            raise ValueError('HTML instead of JSON')
    monkeypatch.setattr(sales.requests, 'get', lambda *a, **k: Bad())
    with pytest.raises(sales.SalesTaxError, match='unreadable'):
        sales.lookup_zip('23220')


def test_local_rate_limit(monkeypatch):
    monkeypatch.setattr(sales, 'MAX_REQUESTS_PER_HOUR', 0)
    monkeypatch.setattr(sales.requests, 'get', lambda *a, **k: pytest.fail('Limit ignored'))
    with pytest.raises(sales.SalesTaxError, match='limit'):
        sales.lookup_zip('23220')


def test_pages_and_existing_tax_paths_work_offline(monkeypatch):
    monkeypatch.setattr(sales.requests, 'get', lambda *a, **k: pytest.fail('Unexpected network request'))
    from app import app
    from pages import home, map_explorer, compare
    from services.census_api import CensusAPIError
    def no_census(*a, **k):
        raise CensusAPIError('Test: no Census key')
    monkeypatch.setattr(home, 'get_county_metrics', no_census)
    for metric in sales.SALES_METRICS:
        figure, table = home.show_sales_comparison(metric)
        assert len(figure.data[0].x) == 51
        result = map_explorer.render_map(None, metric, 'avg_wkly_wage', {})
        assert len(result[0].data[0].locations) == 51
        assert '2026-07-01' in result[-1]
        chart, note = compare.compare_states(['Virginia', 'Texas'], metric, {})
        assert len(chart.data[0].x) == 2
    income_result = home.analyze_income(1, 100000, 'single')
    assert len(income_result[1].data[0].y) == 15
    tax_map = map_explorer.render_map(None, 'estimated_tax', 'avg_wkly_wage', {})
    assert len(tax_map[0].data[0].locations) >= 50
    assert len(tax_map[0].data[0].customdata[0]) == 4
    import pandas as pd
    monkeypatch.setattr(map_explorer, 'bls_counties', lambda _: pd.DataFrame({'fips': ['51001'], 'avg_wkly_wage': [1000]}))
    county_map = map_explorer.render_map('VA', 'sales_combined_average', 'avg_wkly_wage', {})
    assert list(county_map[0].data[-1].locations) == ['51001']
    assert list(county_map[0].data[-1].z) == [1000]
    client = app.server.test_client()
    for path in ['/', '/map', '/compare', '/rankings', '/_dash-layout', '/_dash-dependencies']:
        assert client.get(path).status_code == 200


def test_zip_ui_rejects_wrong_state_and_invalid_spending(monkeypatch):
    from utils.sales_tax_ui import quote_view
    monkeypatch.setattr(sales.requests, 'get', lambda *a, **k: Response(payload()))
    assert 'outside the selected state' in quote_view('23220', 100, 'CA').children
    assert 'Enter a taxable purchase' in quote_view('23220', math.nan).children
