# AI ASSISTANCE DISCLOSURE
# ChatGPT was used to brainstorm architecture, identify/verify public API endpoints,
# draft initial callback/data-cleaning patterns, styling, tests, and documentation.
# The team must review, run, edit, understand, and verify this file and its outputs
# against the linked official sources before submission or presentation.

"""BLS Quarterly Census of Employment and Wages (QCEW) keyless CSV API client."""
from __future__ import annotations

from functools import lru_cache
from io import StringIO
import pandas as pd
import requests

BASE = 'https://data.bls.gov/cew/data/api/{year}/{quarter}/industry/10.csv'
AREA_TITLES = 'https://www.bls.gov/cew/classifications/areas/area-titles-csv.csv'

class BLSAPIError(RuntimeError):
    pass


def _download(year: int, quarter: int) -> pd.DataFrame:
    """Download one nationwide quarterly employment-and-wage CSV from BLS."""
    url = BASE.format(year=year, quarter=quarter)
    try:
        r = requests.get(url, timeout=40)
        r.raise_for_status()
        return pd.read_csv(StringIO(r.text), dtype={'area_fips': str, 'agglvl_code': str})
    except Exception as exc:
        raise BLSAPIError(f'BLS QCEW request failed: {exc}') from exc


@lru_cache(maxsize=8)
def get_qcew(year: int = 2026, quarter: int = 1) -> pd.DataFrame:
    """Clean BLS identifiers and numbers once, then cache the reusable table."""
    df = _download(year, quarter)
    # QCEW aggregation levels 50 = statewide total covered, 70 = county total covered.
    df['agglvl_code'] = df['agglvl_code'].astype(str).str.zfill(2)
    df['area_fips'] = df['area_fips'].astype(str).str.zfill(5)
    numeric = [
        'qtrly_estabs','month1_emplvl','month2_emplvl','month3_emplvl','total_qtrly_wages',
        'avg_wkly_wage','oty_qtrly_estabs_pct_chg','oty_month3_emplvl_pct_chg','oty_avg_wkly_wage_pct_chg'
    ]
    for col in numeric:
        if col in df:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df


@lru_cache(maxsize=8)
def get_state_metrics(year: int = 2026, quarter: int = 1) -> pd.DataFrame:
    """Keep the all-industry total row for each state."""
    df = get_qcew(year, quarter)
    out = df[df['agglvl_code'].eq('50')].copy()
    out['state_fips'] = out['area_fips'].str[:2]
    return out


@lru_cache(maxsize=64)
def get_county_metrics(state_fips: str, year: int = 2026, quarter: int = 1) -> pd.DataFrame:
    """Keep county total rows belonging to one state's two-digit FIPS code."""
    df = get_qcew(year, quarter)
    out = df[df['agglvl_code'].eq('70') & df['area_fips'].str.startswith(str(state_fips).zfill(2))].copy()
    out['fips'] = out['area_fips']
    out['state_fips'] = out['area_fips'].str[:2]
    return out


@lru_cache(maxsize=2)
def get_area_titles() -> pd.DataFrame:
    """Download BLS's lookup table that translates area codes into names."""
    try:
        r = requests.get(AREA_TITLES, timeout=30)
        r.raise_for_status()
        df = pd.read_csv(StringIO(r.text), dtype=str)
    except Exception as exc:
        raise BLSAPIError(f'BLS area-title request failed: {exc}') from exc
    df.columns = [str(c).strip().lower() for c in df.columns]
    code_col = next((c for c in df.columns if 'code' in c or 'fips' in c), df.columns[0])
    title_col = next((c for c in df.columns if 'title' in c or 'name' in c), df.columns[1])
    out = df[[code_col, title_col]].rename(columns={code_col:'area_fips', title_col:'area_title'})
    out['area_fips'] = out['area_fips'].astype(str).str.strip().str.zfill(5)
    out['area_title'] = out['area_title'].astype(str).str.strip()
    return out
