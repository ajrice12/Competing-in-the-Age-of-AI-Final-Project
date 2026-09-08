# AI ASSISTANCE DISCLOSURE
# ChatGPT was used to brainstorm architecture, identify/verify public API endpoints,
# draft initial callback/data-cleaning patterns, styling, tests, and documentation.
# The team must review, run, edit, understand, and verify this file and its outputs
# against the linked official sources before submission or presentation.

from __future__ import annotations

import dash
from dash import Input, Output, callback, dcc, html
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from services.tax_engine import rank_states
from services.bls_qcew import get_state_metrics as bls_states
from services.census_api import get_state_metrics as census_states, CensusAPIError
from utils.geography import STATE_META, FIPS_TO_NAME
from services.sales_tax import SALES_METRICS, source_note, state_sales_taxes

dash.register_page(__name__, path='/compare', name='Compare States')

STATE_OPTIONS = [{'label':name,'value':name} for name in STATE_META if name != 'District of Columbia']
METRICS = {
    **SALES_METRICS,
    'estimated_tax':'Estimated tax at saved income',
    'effective_rate':'Effective tax rate',
    'avg_wkly_wage':'Average weekly wage',
    'job_growth':'Employment growth YoY',
    'median_household_income':'Median household income',
    'poverty_rate':'Poverty rate',
}

layout = html.Div([
    html.P('SIDE-BY-SIDE ANALYSIS', className='eyebrow'),
    html.H2('Compare states'),
    html.P('Pick 2–5 states and compare tax or economic indicators using the same saved income scenario.', className='muted'),
    html.Div([
        html.Div([html.Label('States'), dcc.Dropdown(id='compare-states', options=STATE_OPTIONS, value=['Virginia','North Carolina','Texas'], multi=True)], className='control-block wide'),
        html.Div([html.Label('Metric'), dcc.Dropdown(id='compare-metric', options=[{'label':v,'value':k} for k,v in METRICS.items()], value='estimated_tax', clearable=False)], className='control-block'),
    ], className='control-row'),
    html.Div(id='compare-note', className='status-note'),
    html.Div([dcc.Graph(id='compare-chart', config={'displayModeBar':False})], className='panel')
])

@callback(
    Output('compare-chart','figure'),
    Output('compare-note','children'),
    Input('compare-states','value'),
    Input('compare-metric','value'),
    Input('income-store','data'),
)
def compare_states(states, metric, income_store):
    states = (states or [])[:5]
    if not states:
        fig = go.Figure().add_annotation(text='Select at least one state.', x=.5, y=.5, showarrow=False)
        return fig, 'No states selected.'
    try:
        if metric in SALES_METRICS:
            df = state_sales_taxes()
            df = df[df['state'].isin(states)].copy()
            df['value'] = df[metric]
            note = source_note()
        elif metric in {'estimated_tax','effective_rate'}:
            s = income_store or {'income':100000,'filing_status':'single'}
            df = rank_states(s.get('income',100000), s.get('filing_status','single'))
            df = df[df['state'].isin(states)].copy()
            df['value'] = df[metric]
            note = f'Tax Foundation 2026 simplified estimator at ${float(s.get("income",100000)):,.0f}.'
        elif metric in {'avg_wkly_wage','job_growth'}:
            df = bls_states().copy()
            df['state'] = df['state_fips'].map(FIPS_TO_NAME)
            df = df[df['state'].isin(states)]
            col = 'avg_wkly_wage' if metric == 'avg_wkly_wage' else 'oty_month3_emplvl_pct_chg'
            df['value'] = pd.to_numeric(df[col], errors='coerce')
            note = 'BLS QCEW 2026 Q1.'
        else:
            df = census_states().copy()
            df['state'] = df['state_fips'].map(FIPS_TO_NAME)
            df = df[df['state'].isin(states)]
            df['value'] = df[metric]
            note = 'Census ACS 2024 5-year API.'
        fig = px.bar(df, x='state', y='value', labels={'state':'','value':METRICS[metric]})
        fig.update_layout(template='plotly_white', margin=dict(l=20,r=20,t=20,b=20), height=500)
        fig.update_traces(hovertemplate='<b>%{x}</b><br>%{y:,.2f}<extra></extra>')
        return fig, note
    except CensusAPIError as exc:
        fig = go.Figure().add_annotation(text=str(exc), x=.5, y=.5, showarrow=False)
        return fig, str(exc)
    except Exception as exc:
        fig = go.Figure().add_annotation(text=f'Comparison unavailable: {exc}', x=.5, y=.5, showarrow=False)
        return fig, f'Error: {exc}'
