# Sales-tax comparisons

The home page now includes a nationwide sales-tax chart and table. The Interactive
Map has three sales-tax measures, and state hover details include the same rates
alongside the selected economic/income-tax measure. Compare States supports all
three measures as well. Existing income-tax calculations are unchanged.

## Nationwide data and availability

`data/sales_tax_states.json` contains 50 states and D.C., extracted from the
[Tax Foundation July 1, 2026 table](https://taxfoundation.org/data/all/state/2026-sales-tax-rates-midyear/)
on September 8, 2026. Values are percentages. Local and combined values are
population-weighted statewide averages, not individual county or address rates.
Preserve the source's footnotes: some state figures include mandatory local
components, and New Jersey's negative local average reflects reduced-rate zones.
Hawaii and New Mexico have special gross-receipts tax systems described there.

This small, dated dataset is bundled with the app, so state comparisons work
without API keys, outbound network access, or persistent storage. It is not
advertised as live. Update the snapshot deliberately from a new published table,
keeping the effective date, retrieval date and source URL with it. Validate all
51 records and preserve source precision; do not invent local averages.

## Free API

Home and map pages have optional ZIP-code lookups using
`GET https://salestaxzip.com/api/v1/rate/{zip}`. No signup or API key is required.
See [documentation](https://salestaxzip.com/api) and
[terms](https://salestaxzip.com/terms). Only individual requested ZIP lookups are
used; no scraping or nationwide bulk downloading is performed.

The provider documents 100 requests/hour and January 2026 data. Each accepted
response shows its own data date and a warning when older than 90 days. A live
HTTP response does not imply current tax rates or independently verified data.

Read-only probes during development returned HTTP 200 for 23220, 90210, 10001,
and 99501, and HTTP 404 for 00000. However, 10001 and 90210 returned components
that exceeded their combined rate. The service intentionally rejects these
responses instead of displaying misleading numbers. Successful arithmetic checks
do not prove geographic accuracy. ZIPs can cross jurisdiction boundaries and the
provider's location labels are not used as verified county identities.

## Failure handling and hosting

- Lookups run only after the user clicks, independently of existing callbacks.
- Requests have bounded connect/read timeouts (3/5 seconds).
- Valid responses are cached for 24 hours, with at most 256 entries per process.
- A local budget allows at most 60 provider requests/hour/process. HTTP 429
  pauses new requests for an hour; network/server failures back off for a minute.
- Expired cached quotes may be shown during outages with an explicit older-cache
  label. A new ZIP with no usable quote shows an explanatory message, not zero.
- Invalid JSON, mismatched ZIP/state, missing dates, nonfinite rates, and
  inconsistent breakdowns are rejected. The nationwide table remains available.
- ZIP estimates use a separate taxable-purchase amount; sales-tax percentages
  are not added to income-tax percentages.

The current Render `gunicorn app:server` command defaults to one worker. With
multiple workers or instances, use a shared limiter/cache before increasing
traffic. Runtime caches reset on restart; the bundled state snapshot does not.
No extra dependency, paid service, API key, or persistent disk is needed.

## County coverage limitation

There is no verified complete nationwide county dataset behind this feature.
County choropleths continue to show the existing economic measures. The separate
ZIP panel can show the provider's county/city/other-local components for a
validated response, but it does not recolor counties or claim that a ZIP's rate
applies everywhere within a county. Selecting another state clears the previous
map lookup result, and ZIPs outside the selected state are rejected by the UI.

## Verification

Run `python -m pytest -q` from the app directory. Tests cover the complete offline
state dataset, existing income-tax rendering, sales-tax map/comparison rendering,
cache isolation, zero rates, leading-zero ZIPs, invalid payloads, timeouts,
rate limits, HTTP failures and the observed inconsistent New York response.

AI assistance: Codex implemented this feature and tests. Review data dates and
methodology before presenting the results.
