# AI ASSISTANCE DISCLOSURE
# ChatGPT helped draft the sales-tax comparison, ZIP-result presentation,
# accessibility labels, and explanatory copy. The team must review and
# understand the displayed calculations and limitations.
"""Shared sales-tax panels; callbacks stay independent of economic API calls."""
from datetime import date
import math

from dash import dcc, html
import plotly.express as px

from services.sales_tax import SALES_METRICS, SalesTaxError, lookup_zip, source_note, source_url, state_sales_taxes
from utils.geography import ABBR_TO_NAME


def lookup_panel(prefix):
    return html.Section([
        html.P('LOCAL SALES TAX', className='eyebrow'),
        html.H3('Look up a ZIP-code estimate'),
        html.P('ZIP codes can cross tax boundaries. A result is not a county-wide rate. '
               'The free provider currently documents January 2026 data; each result shows its own date.', className='muted small'),
        html.Div([
            html.Div([html.Label('ZIP code', htmlFor=f'{prefix}-zip'),
                      dcc.Input(id=f'{prefix}-zip', type='text', maxLength=5, placeholder='e.g. 99501', className='input-control')], className='control-block'),
            html.Div([html.Label('Taxable purchase ($)', htmlFor=f'{prefix}-purchase'),
                      dcc.Input(id=f'{prefix}-purchase', type='number', value=100, min=0, max=100000000, className='input-control')], className='control-block'),
            html.Button('Look up sales tax', id=f'{prefix}-lookup', n_clicks=0, className='primary-button'),
        ], className='control-row'),
        dcc.Loading(html.Div(id=f'{prefix}-result', role='status', **{'aria-live': 'polite'}), type='circle'),
        html.P([html.A('Free API source and coverage', href='https://salestaxzip.com/api', target='_blank', rel='noopener noreferrer')], className='muted small'),
    ], className='panel sales-section')


def quote_view(zip_code, purchase, selected_state=None):
    try:
        amount = float(purchase)
        if not math.isfinite(amount) or not 0 <= amount <= 100000000:
            raise ValueError
    except (TypeError, ValueError):
        return html.P('Enter a taxable purchase between $0 and $100,000,000.', className='api-warning')
    try:
        quote = lookup_zip(zip_code)
    except SalesTaxError as exc:
        return html.P(str(exc), className='api-warning')
    if selected_state and selected_state != quote['state']:
        return html.P(f"That ZIP is in {ABBR_TO_NAME[quote['state']]}, outside the selected state. Enter a ZIP in {ABBR_TO_NAME[selected_state]}.", className='api-warning')
    rates = quote['rates']
    cards = [(label, f'{rates[key] * 100:.3f}%') for key, label in
             [('state', 'State component'), ('county', 'County component'), ('city', 'City component'), ('local', 'Other local component'), ('combined', 'Combined ZIP estimate')]]
    cards.append(('Sales tax on this purchase', f"${amount * rates['combined']:,.2f}"))
    age = (date.today() - date.fromisoformat(quote['updated'])).days
    return html.Div([
        html.H4(f"ZIP {quote['zip_code']} • {ABBR_TO_NAME[quote['state']]}"),
        html.P(f"Provider data date: {quote['updated']}. {quote['delivery']}.", className='status-note'),
        html.P('This rate is more than 90 days old; it may have changed.', className='api-warning') if age > 90 else None,
        html.Div([html.Div([html.Span(k, className='stat-label'), html.Strong(v, className='stat-value')], className='stat-card') for k, v in cards], className='stat-grid'),
        html.P('General taxable-purchase estimate only. Product exemptions and address-specific rules are not modeled. '
               'ZIP rates and state averages have different coverage and dates.', className='muted small'),
    ])


def comparison_panel():
    return html.Section([
        html.P('COMPARE SALES TAX', className='eyebrow'),
        html.H3('How do sales taxes compare across states?'),
        html.P('Compare the rate on spending alongside the income-tax estimates above. These percentages use different tax bases and should not be added together.', className='muted'),
        html.Div([
            html.Label('Sales-tax measure', htmlFor='home-sales-metric'),
            dcc.Dropdown(id='home-sales-metric', options=[{'label': v, 'value': k} for k, v in SALES_METRICS.items()], value='sales_combined_average', clearable=False),
        ], className='control-block'),
        html.P([source_note(), ' ', html.A('Source and methodology', href=source_url(), target='_blank', rel='noopener noreferrer')], className='status-note'),
        html.Div(dcc.Graph(id='home-sales-chart', config={'displayModeBar': False}),
                 role='img', **{'aria-label': 'Bar chart comparing state and average local sales-tax rates'}),
        html.Div(id='home-sales-table', className='sales-table-wrap'),
        dcc.Link('Explore sales tax on the map →', href='/map', className='sales-map-link'),
    ], className='panel sales-section')


def comparison_view(metric):
    metric = metric if metric in SALES_METRICS else 'sales_combined_average'
    df = state_sales_taxes().sort_values([metric, 'state'], ascending=[False, True])
    fig = px.bar(df, x='abbr', y=metric, hover_name='state', labels={'abbr': 'State / D.C.', metric: SALES_METRICS[metric]}, custom_data=['sales_state_rate', 'sales_local_average', 'sales_combined_average'])
    fig.update_traces(hovertemplate='<b>%{hovertext}</b><br>State: %{customdata[0]:.3f}%<br>Average local: %{customdata[1]:.3f}%<br>Average combined: %{customdata[2]:.3f}%<extra></extra>')
    fig.update_traces(marker_color='#315f9c', marker_line_color='#f7f2e7', marker_line_width=.5)
    fig.update_layout(template='plotly_white', height=440, margin=dict(l=20, r=20, t=20, b=60),
                      yaxis_ticksuffix='%', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='#fffdf8')
    table = html.Table([
        html.Caption('All 50 states and D.C. • effective July 1, 2026'),
        html.Thead(html.Tr([html.Th(x, scope='col') for x in ['State', 'State rate', 'Average local', 'Average combined']])),
        html.Tbody([html.Tr([html.Th(row.state, scope='row')] + [html.Td(f'{getattr(row, key):.3f}%') for key in SALES_METRICS]) for row in df.itertuples()]),
    ], className='sales-table')
    return fig, table
