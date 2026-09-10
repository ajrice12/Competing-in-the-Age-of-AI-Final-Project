# AI ASSISTANCE DISCLOSURE
# ChatGPT was used to brainstorm architecture, identify/verify public API endpoints,
# draft initial callback/data-cleaning patterns, styling, tests, and documentation.
# The team must review, run, edit, understand, and verify this file and its outputs
# against the linked official sources before submission or presentation.

from __future__ import annotations

import dash
from dash import Input, Output, State, callback, dcc, html
import plotly.express as px

from services.tax_engine import rank_states
from services.census_api import get_county_metrics, CensusAPIError
from utils.sales_tax_ui import comparison_panel, comparison_view, lookup_panel, quote_view

dash.register_page(__name__, path='/', name='Home')


def _rank_cards(df, highest=True, n=5):
    """Turn the first or last few tax rows into the small ranking cards."""
    use = df.head(n) if highest else df.tail(n).sort_values('estimated_tax')
    return [
        html.Div([
            html.Span(f'{i}. {row.state}', className='rank-name'),
            html.Span(f'${row.estimated_tax:,.0f}  •  {row.effective_rate:.2f}%', className='rank-value')
        ], className='rank-row')
        for i, row in enumerate(use.itertuples(), start=1)
    ]

layout = html.Div([
    html.Section([
        html.Div([
            html.P('PERSONALIZED STATE TAX SCENARIO', className='eyebrow'),
            html.H2('If I earn this much, which states take the largest share?'),
            html.P(
                'Enter annual wage income. The app estimates 2026 state individual income tax, '
                'then connects the result to live/current government economic indicators.'
            ),
        ], className='hero-copy'),
        html.Div([
            html.Label('Annual wage income', htmlFor='income-input'),
            dcc.Input(id='income-input', type='number', value=100000, min=0, step=5000, debounce=True, className='input-control'),
            html.Label('Filing status', htmlFor='filing-status'),
            dcc.Dropdown(
                id='filing-status',
                options=[{'label':'Single','value':'single'}, {'label':'Married filing jointly','value':'joint'}],
                value='single', clearable=False, className='dropdown-control'
            ),
            html.Button('Analyze my income', id='analyze-income', n_clicks=0, className='primary-button'),
        ], className='hero-form')
    ], className='hero-grid'),

    html.Div(id='home-status', className='status-note'),

    html.Section([
        html.Div([html.P('Highest estimated state taxes', className='card-kicker'), html.Div(id='highest-states')], className='panel'),
        html.Div([html.P('Lowest estimated state taxes', className='card-kicker'), html.Div(id='lowest-states')], className='panel'),
        html.Div([
            html.P('County tax-pressure proxy', className='card-kicker'),
            html.P('Median real-estate tax paid ÷ median household income × 100, using 2024 ACS county estimates. '
                   'It is a broad housing-cost pressure signal—not a county sales-tax rate or a personalized tax bill.',
                   className='muted small'),
            html.Div(id='county-tax-ranking')
        ], className='panel'),
    ], className='three-col'),

    html.Section([
        html.Div([
            html.H3('Estimated 2026 state income tax at your income'),
            html.P('Simplified estimator; local income taxes and many credits/special rules are excluded.', className='muted'),
            dcc.Graph(id='tax-ranking-chart', config={'displayModeBar': False})
        ], className='panel', role='img', **{'aria-label': 'Ranking chart of estimated state income taxes'})
    ]),
    comparison_panel(),
    lookup_panel('home-sales'),
])


@callback(Output('home-sales-chart', 'figure'), Output('home-sales-table', 'children'), Input('home-sales-metric', 'value'))
def show_sales_comparison(metric):
    """Redraw the sales-tax chart and table when its measure changes."""
    return comparison_view(metric)


@callback(Output('home-sales-result', 'children'), Input('home-sales-lookup', 'n_clicks'),
          State('home-sales-zip', 'value'), State('home-sales-purchase', 'value'), prevent_initial_call=True)
def show_sales_lookup(clicks, zip_code, purchase):
    """Run the ZIP lookup only after the user clicks its button."""
    return quote_view(zip_code, purchase)


@callback(
    Output('income-store', 'data'),
    Output('tax-ranking-chart', 'figure'),
    Output('highest-states', 'children'),
    Output('lowest-states', 'children'),
    Output('county-tax-ranking', 'children'),
    Output('home-status', 'children'),
    Input('analyze-income', 'n_clicks'),
    State('income-input', 'value'),
    State('filing-status', 'value'),
)
def analyze_income(_clicks, income, filing_status):
    """Validate the scenario, rank states, and refresh every home-page result."""
    try:
        income = max(float(income or 0), 0)
    except (TypeError, ValueError):
        income = 100000.0
    filing_status = filing_status if filing_status in {'single','joint'} else 'single'
    df = rank_states(income, filing_status)
    top15 = df.head(15).sort_values('estimated_tax')
    fig = px.bar(
        top15, x='estimated_tax', y='state', orientation='h',
        labels={'estimated_tax':'Estimated state income tax ($)','state':''},
        custom_data=['effective_rate']
    )
    fig.update_traces(hovertemplate='<b>%{y}</b><br>Tax: $%{x:,.0f}<br>Effective rate: %{customdata[0]:.2f}%<extra></extra>')
    fig.update_traces(marker_color='#315f9c', marker_line_color='#f7f2e7', marker_line_width=.5)
    fig.update_layout(margin=dict(l=10,r=10,t=10,b=10), height=470, template='plotly_white',
                      paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='#fffdf8')

    # Census is optional, so an API problem should not break the tax estimator.
    county_children = []
    county_status = 'BLS map metrics work without keys. Census county tax-pressure rankings need CENSUS_API_KEY.'
    try:
        c = get_county_metrics()
        c = c.dropna(subset=['property_tax_income_pct','median_real_estate_tax','median_household_income'])
        c = c[c['median_household_income'] > 0].nlargest(5, 'property_tax_income_pct')
        county_children = [
            html.Div([
                html.Span(f'{i}. {row.county_name}', className='rank-name'),
                html.Span(f'{row.property_tax_income_pct:.2f}%  •  ${row.median_real_estate_tax:,.0f}', className='rank-value')
            ], className='rank-row')
            for i, row in enumerate(c.itertuples(), 1)
        ]
        county_status = 'Census ACS connected. County tax-pressure proxy is using 2024 ACS 5-year estimates.'
    except CensusAPIError as exc:
        county_children = html.Div([
            html.P(str(exc)),
            html.A('Request and activate a free Census API key',
                   href='https://api.census.gov/data/key_signup.html', target='_blank', rel='noopener noreferrer')
        ], className='api-warning')
    except Exception as exc:
        county_children = html.Div(f'County ranking unavailable: {exc}', className='api-warning')

    return (
        {'income': income, 'filing_status': filing_status}, fig,
        _rank_cards(df, True), _rank_cards(df, False), county_children,
        f'Income scenario: ${income:,.0f} • {"Single" if filing_status == "single" else "Married filing jointly"}. {county_status}'
    )
