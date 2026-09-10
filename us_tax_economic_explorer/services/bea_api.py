# AI ASSISTANCE DISCLOSURE
# ChatGPT was used to brainstorm architecture, identify/verify public API endpoints,
# draft initial callback/data-cleaning patterns, styling, tests, and documentation.
# The team must review, run, edit, understand, and verify this file and its outputs
# against the linked official sources before submission or presentation.

"""Optional BEA Regional API client for state/county GDP and personal income."""
from __future__ import annotations

import os
from functools import lru_cache
import pandas as pd
import requests

BASE = 'https://apps.bea.gov/api/data/'

class BEAAPIError(RuntimeError):
    pass


def _key() -> str:
    """Read the optional BEA key and explain what is missing when unset."""
    key = os.getenv('BEA_API_KEY', '').strip()
    if not key:
        raise BEAAPIError('BEA metrics require BEA_API_KEY in .env.')
    return key


def _get(table: str, line_code: str, year: str, geofips: str) -> pd.DataFrame:
    """Send a Regional-data query to BEA and return its result rows as a table."""
    params = {
        'UserID': _key(), 'method': 'GetData', 'datasetname': 'Regional',
        'TableName': table, 'LineCode': line_code, 'Year': year,
        'GeoFips': geofips, 'ResultFormat': 'JSON'
    }
    try:
        r = requests.get(BASE, params=params, timeout=30)
        r.raise_for_status()
        payload = r.json()
        rows = payload['BEAAPI']['Results']['Data']
        return pd.DataFrame(rows)
    except Exception as exc:
        raise BEAAPIError(f'BEA API request failed: {exc}') from exc


def _num(s: pd.Series) -> pd.Series:
    """Remove BEA commas and missing markers before converting text to numbers."""
    return pd.to_numeric(s.astype(str).str.replace(',', '', regex=False).str.replace('(NA)', '', regex=False), errors='coerce')


@lru_cache(maxsize=4)
def get_state_real_gdp(year: str = '2024') -> pd.DataFrame:
    """Return real GDP and state FIPS codes for the national state map."""
    # Official BEA API guide example uses SAGDP9N LineCode=2 for real GDP, all states.
    df = _get('SAGDP9N', '2', year, 'STATE')
    df['state_fips'] = df['GeoFIPS'].astype(str).str.strip().str[:2]
    df['real_gdp_millions'] = _num(df['DataValue'])
    return df[['state_fips','GeoName','real_gdp_millions','Year']]


@lru_cache(maxsize=8)
def get_county_personal_income(year: str = '2024') -> pd.DataFrame:
    """Return personal income and five-digit FIPS codes for all counties."""
    # Official guide example: CAINC1 LineCode=1 returns personal income for all counties.
    df = _get('CAINC1', '1', year, 'COUNTY')
    df['fips'] = df['GeoFIPS'].astype(str).str.strip().str[:5]
    df['personal_income_thousands'] = _num(df['DataValue'])
    return df[['fips','GeoName','personal_income_thousands','Year']]
