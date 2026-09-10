# AI ASSISTANCE DISCLOSURE
# ChatGPT was used to brainstorm architecture, identify/verify public API endpoints,
# draft initial callback/data-cleaning patterns, styling, tests, and documentation.
# The team must review, run, edit, understand, and verify this file and its outputs
# against the linked official sources before submission or presentation.

"""U.S. Census ACS 5-year API client (2024 vintage by default)."""
from __future__ import annotations

import os
from functools import lru_cache
import pandas as pd
import requests

BASE = 'https://api.census.gov/data/{year}/acs/acs5'
VARIABLES = {
    'B01003_001E': 'population',
    'B19013_001E': 'median_household_income',
    'B25077_001E': 'median_home_value',
    'B25103_001E': 'median_real_estate_tax',
    'B17001_001E': 'poverty_universe',
    'B17001_002E': 'below_poverty',
}

class CensusAPIError(RuntimeError):
    pass


def _key() -> str:
    """Read the Census key from the environment and give a useful setup error."""
    key = os.getenv('CENSUS_API_KEY', '').strip()
    if not key:
        raise CensusAPIError(
            'Census now requires an activated CENSUS_API_KEY for these ACS queries. '
            'Request the free key, activate the emailed link, and add it to your .env file '
            'locally or to the Render environment. The BLS and tax features still work without it.'
        )
    return key


def _clean_numeric(series: pd.Series) -> pd.Series:
    """Convert Census text values to numbers and blank out missing-value codes."""
    s = pd.to_numeric(series, errors='coerce')
    # ACS uses negative sentinel values for unavailable estimates.
    return s.mask(s < 0)


def _request(params: dict, year: int = 2024) -> pd.DataFrame:
    """Call ACS and turn its header row plus data rows into a DataFrame."""
    params = {**params, 'key': _key()}
    try:
        r = requests.get(BASE.format(year=year), params=params, timeout=25)
        r.raise_for_status()
        payload = r.json()
    except Exception as exc:
        raise CensusAPIError(f'Census API request failed: {exc}') from exc
    if not payload or len(payload) < 2:
        return pd.DataFrame()
    return pd.DataFrame(payload[1:], columns=payload[0])


@lru_cache(maxsize=4)
def get_state_metrics(year: int = 2024) -> pd.DataFrame:
    """Fetch state ACS facts and calculate the two percentages used by the app."""
    get_vars = 'NAME,' + ','.join(VARIABLES)
    df = _request({'get': get_vars, 'for': 'state:*'}, year)
    df = df.rename(columns=VARIABLES)
    for col in VARIABLES.values():
        df[col] = _clean_numeric(df[col])
    df['state_fips'] = df['state'].astype(str).str.zfill(2)
    df['poverty_rate'] = (df['below_poverty'] / df['poverty_universe'] * 100).where(df['poverty_universe'] > 0)
    df['property_tax_income_pct'] = (df['median_real_estate_tax'] / df['median_household_income'] * 100).where(df['median_household_income'] > 0)
    return df


@lru_cache(maxsize=8)
def get_county_metrics(state_fips: str | None = None, year: int = 2024) -> pd.DataFrame:
    """Fetch county ACS facts nationwide or for one state and create full FIPS IDs."""
    get_vars = 'NAME,' + ','.join(VARIABLES)
    params = {'get': get_vars, 'for': 'county:*', 'in': f'state:{state_fips}' if state_fips else 'state:*'}
    df = _request(params, year)
    df = df.rename(columns=VARIABLES)
    for col in VARIABLES.values():
        df[col] = _clean_numeric(df[col])
    df['state_fips'] = df['state'].astype(str).str.zfill(2)
    df['county_fips'] = df['county'].astype(str).str.zfill(3)
    df['fips'] = df['state_fips'] + df['county_fips']
    df['county_name'] = df['NAME'].str.split(',').str[0]
    df['poverty_rate'] = (df['below_poverty'] / df['poverty_universe'] * 100).where(df['poverty_universe'] > 0)
    df['property_tax_income_pct'] = (df['median_real_estate_tax'] / df['median_household_income'] * 100).where(df['median_household_income'] > 0)
    return df
