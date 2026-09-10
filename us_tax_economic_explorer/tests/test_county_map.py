# AI ASSISTANCE DISCLOSURE
# ChatGPT helped draft regression cases for county geometry, API fallbacks, and
# FIPS matching. The team must review and understand each assertion.
import pandas as pd
import pytest

from utils.county_map import county_boundaries, county_figure
from utils.geography import ABBR_TO_FIPS


@pytest.fixture
def maps():
    from app import app
    from pages import map_explorer
    return map_explorer


@pytest.mark.parametrize('abbr', list(ABBR_TO_FIPS))
def test_state_geography_is_local_complete_and_scoped(abbr):
    fips = ABBR_TO_FIPS[abbr]
    geo = county_boundaries(fips)
    fig, matched, count = county_figure(geo)
    assert count > 0 and matched == 0
    assert all(feature['id'].startswith(fips) for feature in geo['features'])
    assert len(fig.data[0].locations) == count
    assert fig.data[0].marker.line.color == 'white'
    assert fig.data[0].locationmode == 'geojson-id'
    assert fig.layout.geo.fitbounds == 'locations'
    assert fig.layout.geo.projection.type == 'mercator'


def test_default_boundaries_need_no_network(maps, monkeypatch):
    monkeypatch.setattr(maps, '_county_df', lambda *a: pytest.fail('Boundary view requested API data'))
    figure, title, back, state_picker, county_picker, note = maps.render_map('VA', 'sales_state_rate', 'boundaries', {})
    assert len(figure.data[0].locations) == 134
    assert title == 'Virginia County Explorer'
    assert back == {} and state_picker == {'display': 'none'} and county_picker == {}
    assert 'No economic API' in note


def test_county_view_defaults_to_api_backed_wage_metric(maps):
    dropdown = next(
        component for component in maps.layout._traverse()
        if getattr(component, 'id', None) == 'county-map-metric'
    )
    assert dropdown.value == 'avg_wkly_wage'


@pytest.mark.parametrize('error', [RuntimeError('timeout'), ValueError('malformed data')])
def test_api_failure_never_replaces_county_map_with_empty_figure(maps, monkeypatch, error):
    def fail(*a):
        raise error
    monkeypatch.setattr(maps, '_county_df', fail)
    figure, title, back, state_picker, county_picker, note = maps.render_map('TX', 'estimated_tax', 'avg_wkly_wage', {})
    assert len(figure.data[0].locations) == 254
    assert title == 'Texas County Explorer'
    assert county_picker == {} and state_picker == {'display': 'none'}
    assert 'unavailable' in note and 'remain available' in note


def test_partial_missing_and_unmatched_data_preserve_all_borders():
    frame = pd.DataFrame({'fips': ['1001', '01003', '01005', '01007', '99999', '01001'],
                          'value': [0, None, float('inf'), 25, 100, 10]})
    fig, matched, count = county_figure(county_boundaries('01'), frame, 'Test measure')
    assert count == 67 and matched == 2
    assert len(fig.data[0].locations) == 67
    assert list(fig.data[1].locations) == ['01001', '01007']
    assert list(fig.data[1].z) == [0, 25]
    assert all(trace.marker.line.color == 'white' for trace in fig.data)
    assert fig.data[1].colorbar.orientation == 'h'
    assert 'No matched data' in fig.data[0].hovertemplate


def test_empty_data_keeps_geography(maps, monkeypatch):
    monkeypatch.setattr(maps, '_county_df', lambda *a: (pd.DataFrame(columns=['fips', 'value']), 'Wage', 'Source.'))
    figure, *_, note = maps.render_map('CA', 'estimated_tax', 'avg_wkly_wage', {})
    assert len(figure.data[0].locations) == 58
    assert '0 of 58' in note


def test_profile_keeps_county_name_during_api_failure(maps, monkeypatch):
    def fail(*a):
        raise RuntimeError('API offline')
    monkeypatch.setattr(maps, 'bls_counties', fail)
    profile = maps.county_profile({'points': [{'location': '51001'}]}, 'VA')
    assert profile.children[0].children == 'Accomack County'
    assert 'boundaries' in profile.children[1].children
