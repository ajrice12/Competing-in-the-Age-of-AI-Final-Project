# AI ASSISTANCE DISCLOSURE
# ChatGPT was used to brainstorm architecture, identify/verify public API endpoints,
# draft initial callback/data-cleaning patterns, styling, tests, and documentation.
# The team must review, run, edit, understand, and verify this file and its outputs
# against the linked official sources before submission or presentation.

"""County boundary GeoJSON loader for Plotly choropleths."""
from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
import requests

PLOTLY_COUNTY_GEOJSON = 'https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json'
LOCAL_PATH = Path(__file__).resolve().parents[1] / 'data' / 'geojson-counties-fips.json'

class GeoJSONError(RuntimeError):
    pass

@lru_cache(maxsize=1)
def get_county_geojson() -> dict:
    """Load bundled county shapes, downloading and saving them only if absent."""
    if LOCAL_PATH.exists() and LOCAL_PATH.stat().st_size > 0:
        return json.loads(LOCAL_PATH.read_text(encoding='utf-8'))
    try:
        r = requests.get(PLOTLY_COUNTY_GEOJSON, timeout=30)
        r.raise_for_status()
        data = r.json()
        try:
            LOCAL_PATH.parent.mkdir(parents=True, exist_ok=True)
            LOCAL_PATH.write_text(json.dumps(data), encoding='utf-8')
        except OSError:
            pass
        return data
    except Exception as exc:
        raise GeoJSONError(f'County boundary download failed: {exc}') from exc
