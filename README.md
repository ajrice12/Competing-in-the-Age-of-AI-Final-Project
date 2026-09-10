# U.S. Tax & Economic Explorer

> **If I earn a given amount, which states have the highest estimated state
> income-tax burden, and how do those states and their counties compare
> economically?**

This team project is a four-page Python Dash app for workers, business analysts,
and regional economic-development staff comparing places to live, work, or
invest. It combines a simplified 2026 income-tax scenario with BLS QCEW,
Census ACS, BEA, state sales-tax, ZIP-rate, and county-boundary data.

The main interaction is a national-to-local drilldown: change the income or map
measure, click a state, then explore its counties and click a county for an
economic profile. The app also provides state comparisons, rankings, sales-tax
comparisons, and a ZIP-code sales-tax estimate.

## Run locally

```bash
cd us_tax_economic_explorer
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:8050`. Copy the repository-root `.env.example` to
`us_tax_economic_explorer/.env` to configure optional Census and BEA keys. BLS,
the tax scenario, and the bundled state/county geography work without keys.

## Documentation

- [Complete project overview, sources, data dictionary, and deployment guide](us_tax_economic_explorer/README.md)
- [County-map reliability and geographic limitations](us_tax_economic_explorer/COUNTY_MAP.md)
- [Sales-tax sources, dates, API limits, and interpretation](us_tax_economic_explorer/SALES_TAX.md)

The repository-root `render.yaml` configures Render with
`us_tax_economic_explorer` as the service root. Add the optional API keys as
secret environment variables when creating the Blueprint.

## Verification

```bash
cd us_tax_economic_explorer
pytest -q
```

The test suite covers tax calculations, geographic joins, county-map fallbacks,
sales-tax parsing, validation, and API error handling.
