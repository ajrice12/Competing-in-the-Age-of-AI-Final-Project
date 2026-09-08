# U.S. Tax & Economic Explorer

A multi-page Python Dash application that answers:

> **If I earn a given amount, which U.S. states have the highest estimated state income-tax burden, and how do those states and their counties compare economically?**

The app combines a simplified 2026 state income-tax estimator with live/current government economic data. Users can enter an income, rank states, hover over a U.S. choropleth, click a state to drill into counties, inspect county labor/economic indicators, compare states, and view national rankings.

## Audience

The intended user is a person comparing places to live or work, a business analyst evaluating state/county markets, or a regional economic-development analyst who wants a fast state-to-county comparison tool.

## Best feature

On **Interactive Map**, hover over states for the selected metric. Click a state and the same map switches to that state's counties. Choose a county metric, hover for values, and click a county to populate the county profile panel. Use **Back to U.S.** to return to the national view.

## Pages

1. **Home / Tax Explorer** — enter annual wage income and filing status; see highest/lowest simplified state income-tax estimates and a county property-tax pressure ranking when Census is connected.
2. **Interactive Map** — U.S. state choropleth with state → county click-through.
3. **Compare States** — compare 2–5 states on tax, wage, employment, income, or poverty indicators.
4. **Rankings** — national top-15 rankings for tax and economic measures.

## Data sources and APIs

### 1) U.S. Bureau of Labor Statistics — QCEW

**Used for:** state/county wages, employment change, establishment counts, establishment growth.

- Open-data guide: https://www.bls.gov/cew/additional-resources/open-data/csv-data-slices.htm
- Keyless API pattern used by the app:
  `https://data.bls.gov/cew/data/api/{year}/{quarter}/industry/10.csv`
- Current project default: **2026 Q1**, all industries (`NAICS 10`).
- QCEW aggregation level `50` = statewide total covered; `70` = county total covered.
- Area-title lookup: https://www.bls.gov/cew/classifications/areas/area-titles-csv.csv

This source works without an API key.

### 2) U.S. Census Bureau — American Community Survey 5-year API

**Used for:** population, median household income, median home value, median real-estate tax, poverty rate, derived property-tax pressure.

- API documentation: https://www.census.gov/data/developers/data-sets/acs-5year/2024.html
- Project vintage: **2024 ACS 5-year**.
- Census currently requires an API key for these calls.
- Request a free key: https://api.census.gov/data/key_signup.html

Example state query structure:

```text
https://api.census.gov/data/2024/acs/acs5?get=NAME,B01003_001E,B19013_001E&for=state:*&key=YOUR_KEY
```

Example county query structure:

```text
https://api.census.gov/data/2024/acs/acs5?get=NAME,B01003_001E,B19013_001E&for=county:*&in=state:51&key=YOUR_KEY
```

### 3) U.S. Bureau of Economic Analysis — Regional API (optional)

**Used for:** optional state real-GDP and county personal-income map metrics.

- API registration/docs: https://apps.bea.gov/api/signup/
- Dataset: `Regional`
- State real GDP call uses `SAGDP9N`, `LineCode=2`.
- County personal income call uses `CAINC1`, `LineCode=1`.

BEA requires a free API key. The rest of the app remains usable without it.

### 4) 2026 state tax-rate/bracket reference

**Used for:** simplified state individual income-tax calculations.

- Tax Foundation, *State Individual Income Tax Rates and Brackets, 2026*: https://taxfoundation.org/data/all/state/state-income-tax-rates-2026/

The tax rules are stored in `services/tax_engine.py`. They are not a live tax-filing API. The calculator models brackets plus selected standard deductions/personal exemptions and intentionally excludes most credits, local income taxes, itemized deductions, capital-gains rules, and special phaseouts.

### 5) County boundary geometry

**Used for:** Plotly county choropleths.

- Plotly county FIPS GeoJSON: https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json

The app downloads this once and caches it in `data/` when possible.

## Data dictionary

| Variable | Source | Level | Meaning |
|---|---|---|---|
| `estimated_tax` | Tax engine | State | Simplified estimated 2026 state individual income tax for entered wage income |
| `effective_rate` | Tax engine | State | `estimated_tax / gross_income * 100` |
| `area_fips` / `fips` | BLS/Census/BEA | State/County | Geographic FIPS identifier used to join data and maps |
| `qtrly_estabs` | BLS QCEW | State/County | Covered establishments in quarter |
| `avg_wkly_wage` | BLS QCEW | State/County | Average weekly wage |
| `oty_month3_emplvl_pct_chg` | BLS QCEW | State/County | Over-the-year employment percent change for quarter's third month |
| `oty_qtrly_estabs_pct_chg` | BLS QCEW | County | Over-the-year establishment-count percent change |
| `population` | Census ACS | State/County | Total population (`B01003_001E`) |
| `median_household_income` | Census ACS | State/County | Median household income (`B19013_001E`) |
| `median_home_value` | Census ACS | State/County | Median owner-occupied home value (`B25077_001E`) |
| `median_real_estate_tax` | Census ACS | State/County | Median real-estate taxes paid (`B25103_001E`) |
| `poverty_universe` | Census ACS | State/County | Population for whom poverty status is determined (`B17001_001E`) |
| `below_poverty` | Census ACS | State/County | People below poverty threshold (`B17001_002E`) |
| `poverty_rate` | Derived | State/County | `below_poverty / poverty_universe * 100` |
| `property_tax_income_pct` | Derived | State/County | `median_real_estate_tax / median_household_income * 100`; a proxy, not a personalized tax bill |
| `real_gdp_millions` | BEA | State | Real GDP value returned by BEA Regional API |
| `personal_income_thousands` | BEA | County | County personal income returned by BEA Regional API |

## Cleaning and transformation performed

The project demonstrates real data cleaning rather than using pre-cleaned chart data:

- converts API strings to numeric fields;
- pads and standardizes state/county FIPS codes;
- maps state FIPS to USPS abbreviations for Plotly;
- filters QCEW aggregation levels so only statewide totals (`50`) and county totals (`70`) remain;
- removes negative ACS sentinel values used for unavailable estimates;
- derives poverty rates and the property-tax pressure ratio;
- joins county codes to BLS area titles;
- handles missing API keys and network/API failures with user-facing messages.

## Local setup

### 1. Create a virtual environment

```bash
python -m venv .venv
```

Activate it.

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

### 2. Install packages

```bash
pip install -r requirements.txt
```

### 3. Configure API keys

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Add your Census key:

```text
CENSUS_API_KEY=your_key_here
```

Optionally add a BEA key:

```text
BEA_API_KEY=your_key_here
```

**Without any keys:** the tax estimator and BLS QCEW state/county metrics still work. Census/BEA-only metrics show an explanatory message instead of crashing.

### 4. Run

```bash
python app.py
```

Open:

```text
http://127.0.0.1:8050
```

## Render deployment

A starter `render.yaml` is included.

1. Push this folder to GitHub.
2. Create a Render Blueprint/Web Service from the repository.
3. Add `CENSUS_API_KEY` and optional `BEA_API_KEY` as secret environment variables.
4. Build command: `pip install -r requirements.txt`
5. Start command: `gunicorn app:server`

## Interactivity / callbacks

The app exceeds the assignment minimum of four meaningful callbacks. Examples:

- income + filing status → tax ranking chart, top/bottom states, saved income scenario;
- state-map metric → U.S. choropleth recoloring;
- click state → selected-state store → county map drill-down;
- county metric → county choropleth recoloring;
- click county → county detail panel;
- compare-state selections → comparison chart;
- ranking metric → ranking chart + table.

## Tests

The included tests cover tax-estimator behavior and geography helpers.

```bash
pytest -q
```

Network/API tests are intentionally not required for the basic test run.

## Known limitations

- “Live” means the **latest published government data**, not real-time transactions. QCEW is quarterly; ACS is annual; BEA regional releases follow their own schedule.
- The tax calculator is intentionally simplified and should be labeled **Estimated State Individual Income Tax**, not “total taxes.”
- Local/county income taxes are not comprehensively modeled. County tax comparison therefore uses an ACS property-tax pressure proxy.
- Connecticut QCEW county geography changed to planning regions beginning with 2024 data; cross-source county joins may need special handling if combining Connecticut BLS and older Census/BEA geography.

## AI assistance disclosure

ChatGPT was used to help brainstorm the project architecture, identify official APIs, draft callback patterns, create an initial version of the tax-estimator logic, build error-handling patterns, draft styling, and generate initial tests/documentation. All submitted code should be reviewed, edited, run, and understood by the team. Government API fields, tax rates/brackets, and outputs should be verified by the team against the linked primary/official sources before presentation or submission.
# Sales-tax addition

The home page, state choropleth, and Compare States page now include sales-tax
comparisons. Free ZIP lookups are also available on home and map pages.
See [SALES_TAX.md](SALES_TAX.md) for source dates, API limitations, county coverage,
and failure handling. No additional API key is required.
