# AI ASSISTANCE DISCLOSURE
# ChatGPT helped identify the public ZIP endpoint, draft validation and
# normalization logic, and document source limitations. The team must review,
# understand, and verify rates and behavior before submission.
"""Free, bounded ZIP lookups and an offline nationwide comparison snapshot.

AI assistance: Codex implemented this service and its failure-path tests.
ZIP estimates are not county-wide rates. Never infer county FIPS from a ZIP.
"""
from __future__ import annotations

from collections import OrderedDict, deque
from copy import deepcopy
from datetime import datetime, timezone
from functools import lru_cache
import json
import math
from pathlib import Path
import re
from threading import Lock
from time import monotonic

import pandas as pd
import requests

from utils.geography import ABBR_TO_NAME

API_URL = 'https://salestaxzip.com/api/v1/rate/'
API_DOCS = 'https://salestaxzip.com/api'
SNAPSHOT = Path(__file__).resolve().parents[1] / 'data' / 'sales_tax_states.json'
SALES_METRICS = {
    'sales_state_rate': 'State sales-tax rate (%)',
    'sales_local_average': 'Average local sales-tax rate (%)',
    'sales_combined_average': 'Average combined sales-tax rate (%)',
}
CACHE_SECONDS = 86400
MAX_CACHE = 256
# Per-process budget below the provider's documented 100/hour limit.
# The existing Render command uses one gunicorn worker. Multiple instances
# would need a shared limiter; a provider 429 is still handled gracefully.
MAX_REQUESTS_PER_HOUR = 60
_cache = OrderedDict()
_requests = deque()
_lock = Lock()
_blocked_until = 0.0


class SalesTaxError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _snapshot():
    """Read the saved 50-state comparison file once per running process."""
    return json.loads(SNAPSHOT.read_text(encoding='utf-8'))


def state_sales_taxes():
    """Return a fresh table so callers cannot change the cached snapshot."""
    return pd.DataFrame(_snapshot()['states']).copy()


def source_note():
    """Create the source and limitation note displayed beside comparisons."""
    data = _snapshot()
    return (f"Tax Foundation • effective {data['effective_date']} • saved comparison dataset. "
            'Local and combined rates are population-weighted state averages, not county or address rates. '
            'Some state rates include mandatory local components; see source footnotes.')


def source_url():
    """Return the original source link stored with the saved state data."""
    return _snapshot()['source_url']


def _rate(value):
    """Accept only a finite decimal rate between zero and 30 percent."""
    if isinstance(value, bool):
        raise ValueError('Boolean rate')
    number = float(value)
    if not math.isfinite(number) or not 0 <= number <= .3:
        raise ValueError('Rate outside expected range')
    return number


def _validate(payload, zip_code):
    """Reject incomplete or contradictory ZIP results before displaying them."""
    try:
        if payload.get('success') is not True:
            raise ValueError('Unsuccessful lookup')
        data = payload['data']
        if data['zip_code'] != zip_code or data['state'] not in ABBR_TO_NAME:
            raise ValueError('Mismatched location')
        rates = {key: _rate(data['rates'][key]) for key in ('combined', 'state', 'county', 'city', 'local')}
        if rates['combined'] < rates['state']:
            raise ValueError('Combined rate below state rate')
        # Real probes found double-counted local components. Reject the entire
        # quote rather than presenting an internally inconsistent breakdown.
        if abs(sum(rates[key] for key in ('state', 'county', 'city', 'local')) - rates['combined']) > .00001:
            raise ValueError('Components do not match total')
        updated = datetime.fromisoformat(data['last_updated'].replace('Z', '+00:00'))
        if updated.tzinfo is None or updated > datetime.now(timezone.utc):
            raise ValueError('Invalid update date')
        return dict(zip_code=zip_code, state=data['state'], rates=rates,
                    updated=updated.date().isoformat(), fetched=datetime.now(timezone.utc).isoformat())
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError) as exc:
        raise SalesTaxError('The provider returned inconsistent or incomplete rates. No ZIP estimate is shown; use the state comparison below.') from exc


def lookup_zip(zip_code):
    """One request per user lookup; cache, backoff and limits survive page changes.

    No API request happens at import or on page load. Runtime caches are
    deliberately ephemeral; the bundled nationwide dataset survives restarts.
    """
    global _blocked_until
    zip_code = str(zip_code or '').strip()
    if not re.fullmatch(r'[0-9]{5}', zip_code):
        raise SalesTaxError('Enter a five-digit U.S. ZIP code, including any leading zero.')
    with _lock:
        now = monotonic()
        cached = _cache.get(zip_code)
        if cached and now - cached[0] < CACHE_SECONDS:
            _cache.move_to_end(zip_code)
            return dict(deepcopy(cached[1]), delivery='Cached API response (up to 24 hours)')
        while _requests and now - _requests[0] >= 3600:
            _requests.popleft()
        if now < _blocked_until or len(_requests) >= MAX_REQUESTS_PER_HOUR:
            return _fallback(cached, 'Free lookup limit reached. Try again later.')
        _requests.append(now)
        try:
            response = requests.get(API_URL + zip_code, timeout=(3, 5), headers={'Accept': 'application/json'})
            if response.status_code == 404:
                raise SalesTaxError('No sales-tax record was found for that ZIP code.')
            if response.status_code == 429:
                _blocked_until = monotonic() + 3600
                return _fallback(cached, 'The free provider is rate-limited. Try again later.')
            response.raise_for_status()
            quote = _validate(response.json(), zip_code)
            _cache[zip_code] = (monotonic(), quote)
            _cache.move_to_end(zip_code)
            while len(_cache) > MAX_CACHE:
                _cache.popitem(last=False)
            return dict(deepcopy(quote), delivery='API response received now; see provider data date')
        except requests.RequestException:
            _blocked_until = monotonic() + 60
            return _fallback(cached, 'The sales-tax provider is temporarily unavailable.')
        except ValueError as exc:
            raise SalesTaxError('The provider returned an unreadable response. State comparisons remain available.') from exc


def _fallback(cached, message):
    """Use an older valid quote when possible; otherwise show a clear error."""
    if cached:
        return dict(deepcopy(cached[1]), delivery=f'{message} Showing an older cached estimate.', stale=True)
    raise SalesTaxError(message + ' The saved state comparison remains available.')
