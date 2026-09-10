# AI ASSISTANCE DISCLOSURE
# ChatGPT was used to brainstorm architecture, identify/verify public API endpoints,
# draft initial callback/data-cleaning patterns, styling, tests, and documentation.
# The team must review, run, edit, understand, and verify this file and its outputs
# against the linked official sources before submission or presentation.

from __future__ import annotations

import dash
from dash import Input, Output, State, callback, ctx, dcc, html
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from services.tax_engine import rank_states
from services.bls_qcew import get_state_metrics as bls_states, get_county_metrics as bls_counties, BLSAPIError
from services.census_api import get_state_metrics as census_states, get_county_metrics as census_counties, CensusAPIError
from services.bea_api import get_state_real_gdp, get_county_personal_income, BEAAPIError
from services.geojson import GeoJSONError
from utils.geography import FIPS_TO_ABBR, ABBR_TO_NAME, ABBR_TO_FIPS, FIPS_TO_NAME
from services.sales_tax import SALES_METRICS, state_sales_taxes, source_note, source_url
from utils.sales_tax_ui import lookup_panel, quote_view
from utils.county_map import county_boundaries, county_figure

dash.register_page(__name__, path='/map', name='Interactive Map')

STATE_METRICS = {
    **{key: (label, 'sales') for key, label in SALES_METRICS.items()},
    'estimated_tax': ('Estimated state income tax', 'tax'),
    'effective_rate': ('Effective state income-tax rate', 'tax'),
    'avg_wkly_wage': ('Average weekly wage — BLS QCEW 2026 Q1', 'bls'),
    'job_growth': ('Employment growth YoY — BLS QCEW 2026 Q1', 'bls'),
    'establishments': ('Business establishments — BLS QCEW 2026 Q1', 'bls'),
    'median_household_income': ('Median household income — ACS 2024', 'census'),
    'poverty_rate': ('Poverty rate — ACS 2024', 'census'),
    'population': ('Population — ACS 2024', 'census'),
    'property_tax_income_pct': ('Property-tax pressure proxy — ACS 2024', 'census'),
    'real_gdp_millions': ('Real GDP — BEA Regional', 'bea'),
}

COUNTY_METRICS = {
    'boundaries': ('County boundaries — no API needed', 'geography'),
    'avg_wkly_wage': ('Average weekly wage — BLS QCEW 2026 Q1', 'bls'),
    'job_growth': ('Employment growth YoY — BLS QCEW 2026 Q1', 'bls'),
    'establishments': ('Business establishments — BLS QCEW 2026 Q1', 'bls'),
    'establishment_growth': ('Establishment growth YoY — BLS QCEW 2026 Q1', 'bls'),
    'median_household_income': ('Median household income — ACS 2024', 'census'),
    'poverty_rate': ('Poverty rate — ACS 2024', 'census'),
    'median_home_value': ('Median owner-occupied home value — ACS 2024', 'census'),
    'property_tax_income_pct': ('Property-tax pressure proxy — ACS 2024', 'census'),
    'personal_income_thousands': ('Personal income — BEA Regional', 'bea'),
}

layout = html.Div([
    dcc.Store(id='selected-state', data=None),
    html.Div([
        html.Div([
            html.P('STATE → COUNTY DRILL-DOWN', className='eyebrow'),
            html.H2(id='map-title', children='U.S. State Economic Map'),
            html.P('Hover for detail. Click any state to replace the U.S. map with its county map.', className='muted'),
        ]),
        html.Button('← Back to U.S.', id='back-to-us', n_clicks=0, className='secondary-button', style={'display':'none'})
    ], className='section-header-row'),

    html.Div([
        html.Div([
            html.Label('State map metric'),
            dcc.Dropdown(
                id='state-map-metric',
                options=[{'label':label,'value':key} for key,(label,_) in STATE_METRICS.items()],
                value='estimated_tax', clearable=False
            )
        ], id='state-metric-wrap', className='control-block'),
        html.Div([
            html.Label('County map metric'),
            dcc.Dropdown(
                id='county-map-metric',
                options=[{'label':label,'value':key} for key,(label,_) in COUNTY_METRICS.items()],
                value='avg_wkly_wage', clearable=False
            )
        ], id='county-metric-wrap', className='control-block', style={'display':'none'}),
    ], className='control-row'),

    html.Div(id='map-source-note', className='status-note'),
    html.Div([
        dcc.Loading(dcc.Graph(id='economic-map', config={'displayModeBar': False}, style={'height':'650px'}), type='circle',
                    overlay_style={'visibility': 'visible', 'opacity': .6})
    ], className='panel map-panel', role='img',
       **{'aria-label': 'Interactive choropleth map of U.S. states with county drilldown'}),
    html.Div(id='county-profile', className='panel'),
    html.P(['Sales-tax colors are available at state level. County maps retain economic indicators; '
            'a ZIP lookup below provides a separate local estimate, not a county-wide rate. ',
            html.A('State sales-tax source', href=source_url(), target='_blank', rel='noopener noreferrer')], className='status-note'),
    lookup_panel('map-sales'),
])


@callback(Output('map-sales-result', 'children'), Input('map-sales-lookup', 'n_clicks'),
          Input('selected-state', 'data'), State('map-sales-zip', 'value'), State('map-sales-purchase', 'value'),
          prevent_initial_call=True)
def show_map_sales_lookup(clicks, selected_state, zip_code, purchase):
    if ctx.triggered_id != 'map-sales-lookup' or not clicks:
        return html.P('Enter a ZIP code and select Look up sales tax for this view.', className='muted small')
    return quote_view(zip_code, purchase, selected_state)


def _empty_figure(message: str):
    fig = go.Figure()
    fig.add_annotation(text=message, x=.5, y=.5, xref='paper', yref='paper', showarrow=False, font={'size':16})
    fig.update_layout(template='plotly_white', margin=dict(l=20,r=20,t=20,b=20))
    return fig


def _state_df(metric: str, income_store: dict | None):
    label, source = STATE_METRICS[metric]
    if source == 'sales':
        df = state_sales_taxes()
        df['value'] = df[metric]
        return df[['state', 'abbr', 'value']], label, source_note()
    if source == 'tax':
        store = income_store or {'income':100000,'filing_status':'single'}
        df = rank_states(store.get('income',100000), store.get('filing_status','single')).copy()
        df['value'] = df[metric]
        return df[['state','abbr','value']], label, 'Tax Foundation 2026 rate/bracket table; simplified estimator.'
    if source == 'bls':
        df = bls_states().copy()
        df['abbr'] = df['state_fips'].map(FIPS_TO_ABBR)
        df['state'] = df['state_fips'].map(FIPS_TO_NAME)
        col = {'avg_wkly_wage':'avg_wkly_wage','job_growth':'oty_month3_emplvl_pct_chg','establishments':'qtrly_estabs'}[metric]
        df['value'] = pd.to_numeric(df[col], errors='coerce')
        return df.dropna(subset=['abbr'])[['state','abbr','value']], label, 'Live/keyless BLS QCEW 2026 Q1 industry 10 (all industries).'
    if source == 'census':
        df = census_states().copy()
        df['abbr'] = df['state_fips'].map(FIPS_TO_ABBR)
        df['state_name'] = df['state_fips'].map(FIPS_TO_NAME)
        df['value'] = df[metric]
        return df.dropna(subset=['abbr'])[['state_name','abbr','value']].rename(columns={'state_name':'state'}), label, 'Census ACS 2024 5-year API.'
    df = get_state_real_gdp().copy()
    df['abbr'] = df['state_fips'].map(FIPS_TO_ABBR)
    df['state'] = df['state_fips'].map(FIPS_TO_NAME)
    df['value'] = df['real_gdp_millions']
    return df.dropna(subset=['abbr'])[['state','abbr','value']], label, 'BEA Regional API.'


def _county_df(state_abbr: str, metric: str):
    state_fips = ABBR_TO_FIPS[state_abbr]
    label, source = COUNTY_METRICS[metric]
    if source == 'bls':
        df = bls_counties(state_fips).copy()
        col = {
            'avg_wkly_wage':'avg_wkly_wage', 'job_growth':'oty_month3_emplvl_pct_chg',
            'establishments':'qtrly_estabs', 'establishment_growth':'oty_qtrly_estabs_pct_chg'
        }[metric]
        df['value'] = pd.to_numeric(df[col], errors='coerce')
        df['county_name'] = df['fips']  # The map uses names from its local boundary file.
        return df[['fips','county_name','value']], label, 'Live/keyless BLS QCEW 2026 Q1 county totals.'
    if source == 'census':
        df = census_counties(state_fips).copy()
        df['value'] = df[metric]
        return df[['fips','county_name','value']], label, 'Census ACS 2024 5-year API.'
    df = get_county_personal_income().copy()
    df = df[df['fips'].str.startswith(state_fips)]
    df['county_name'] = df['GeoName']
    df['value'] = df['personal_income_thousands']
    return df[['fips','county_name','value']], label, 'BEA Regional API.'


@callback(
    Output('selected-state', 'data'),
    Input('economic-map', 'clickData'),
    Input('back-to-us', 'n_clicks'),
    State('selected-state', 'data'),
    prevent_initial_call=True,
)
def choose_state(click_data, _back, current):
    if ctx.triggered_id == 'back-to-us':
        return None
    if not click_data or not click_data.get('points'):
        return current
    loc = str(click_data['points'][0].get('location',''))
    if len(loc) == 2 and loc in ABBR_TO_NAME:
        return loc
    return current


@callback(
    Output('economic-map','figure'),
    Output('map-title','children'),
    Output('back-to-us','style'),
    Output('state-metric-wrap','style'),
    Output('county-metric-wrap','style'),
    Output('map-source-note','children'),
    Input('selected-state','data'),
    Input('state-map-metric','value'),
    Input('county-map-metric','value'),
    Input('income-store','data'),
   
)
def render_map(selected_state, state_metric, county_metric, income_store):
    try:
        if not selected_state:
            df, label, note = _state_df(state_metric, income_store)
            sales = state_sales_taxes()[['abbr', *SALES_METRICS]]
            df = df.merge(sales, on='abbr', how='left', validate='one_to_one')
            fig = px.choropleth(
                df, locations='abbr', locationmode='USA-states', color='value', scope='usa',
                hover_name='state', custom_data=['value', *SALES_METRICS],
                color_continuous_scale='Magma'
            )
            suffix = '%' if state_metric in SALES_METRICS else ''
            fig.update_traces(hovertemplate='<b>%{hovertext}</b><br>'+label+': %{customdata[0]:,.3f}'+suffix+
                              '<br><br>Sales tax • July 1, 2026<br>State: %{customdata[1]:.3f}%'
                              '<br>Average local: %{customdata[2]:.3f}%<br>Average combined: %{customdata[3]:.3f}%'
                              '<br>State averages; not address rates<extra></extra>')
            fig.update_layout(margin=dict(l=0,r=0,t=10,b=0), coloraxis_colorbar_title=label,
                              paper_bgcolor='rgba(0,0,0,0)')
            return fig, 'U.S. State Economic Map', {'display':'none'}, {}, {'display':'none'}, note

        geojson = county_boundaries(ABBR_TO_FIPS[selected_state])
        if county_metric == 'boundaries':
            fig, _, count = county_figure(geojson)
            note = (f'{count} county / county-equivalent boundaries. Hover for names; click for details. '
                    'Choose an economic measure above to color the counties. No economic API is needed for this boundary view.')
        else:
            try:
                df, label, note = _county_df(selected_state, county_metric)
                fig, matched, count = county_figure(geojson, df, label)
                note += (f' Data matched to {matched} of {count} displayed county boundaries. '
                         'Counties without matched data stay slate blue; white lines show every boundary.')
            except Exception as exc:
                fig, _, count = county_figure(geojson)
                note = (f'{count} county boundaries remain available. The selected economic measure is unavailable: {exc}. '
                        'Choose County boundaries or another measure. No missing values are displayed as zero.')
        return fig, f'{ABBR_TO_NAME[selected_state]} County Explorer', {}, {'display':'none'}, {}, note
    except (CensusAPIError, BEAAPIError, BLSAPIError, GeoJSONError) as exc:
        return _empty_figure(str(exc)), 'Data source needs attention', ({'display':'none'} if not selected_state else {}), {}, {'display':'none'} if not selected_state else {}, str(exc)
    except Exception as exc:
        return _empty_figure(f'Unable to draw map: {exc}'), 'Map unavailable', ({'display':'none'} if not selected_state else {}), {}, {'display':'none'} if not selected_state else {}, f'Error: {exc}'


@callback(
    Output('county-profile','children'),
    Input('economic-map','clickData'),
    Input('selected-state','data'),
)
def county_profile(click_data, selected_state):
    if not selected_state:
        return html.Div([html.H3('How to use the map'), html.P('Hover over states for values. Click a state to drill into counties.')])
    if not click_data or not click_data.get('points'):
        return html.Div([html.H3(f'{ABBR_TO_NAME[selected_state]}'), html.P('Click a county for a profile.')])
    fips = str(click_data['points'][0].get('location',''))
    if len(fips) != 5 or not fips.startswith(ABBR_TO_FIPS[selected_state]):
        return html.Div([html.H3(f'{ABBR_TO_NAME[selected_state]}'), html.P('Click a county for a profile.')])
    county_name = fips
    for feature in county_boundaries(ABBR_TO_FIPS[selected_state])['features']:
        if feature['id'] == fips:
            properties = feature.get('properties', {})
            county_name = f"{properties.get('NAME', fips)} {properties.get('LSAD', '')}".strip()
            break
    try:
        b = bls_counties(ABBR_TO_FIPS[selected_state])
        row = b[b['fips'].eq(fips)].head(1)
        if row.empty:
            return html.Div([html.H3(county_name), html.P('No BLS record matches this county boundary. The county map remains available.', className='api-warning')])
        r = row.iloc[0]
        cards = [
            ('Average weekly wage', f'${float(r.get("avg_wkly_wage",0)):,.0f}'),
            ('Employment growth YoY', f'{float(r.get("oty_month3_emplvl_pct_chg",0)):.1f}%'),
            ('Establishments', f'{float(r.get("qtrly_estabs",0)):,.0f}'),
            ('Establishment growth YoY', f'{float(r.get("oty_qtrly_estabs_pct_chg",0)):.1f}%'),
        ]
        try:
            c = census_counties(ABBR_TO_FIPS[selected_state])
            cr = c[c['fips'].eq(fips)].head(1)
            if not cr.empty:
                cr = cr.iloc[0]
                cards += [
                    ('Median household income', f'${float(cr.get("median_household_income",0)):,.0f}'),
                    ('Median property tax', f'${float(cr.get("median_real_estate_tax",0)):,.0f}'),
                    ('Poverty rate', f'{float(cr.get("poverty_rate",0)):.1f}%'),
                    ('Median home value', f'${float(cr.get("median_home_value",0)):,.0f}'),
                ]
        except Exception:
            pass
        return html.Div([
            html.Div([html.P('COUNTY PROFILE', className='eyebrow'), html.H3(county_name)]),
            html.Div([html.Div([html.Span(k, className='stat-label'), html.Strong(v, className='stat-value')], className='stat-card') for k,v in cards], className='stat-grid'),
            html.P('BLS values are 2026 Q1. Census values appear when CENSUS_API_KEY is configured.', className='muted small')
        ])
    except Exception as exc:
        return html.Div([html.H3(county_name), html.P(f'County economic data unavailable: {exc}. You can still explore the county boundaries.', className='api-warning')])
