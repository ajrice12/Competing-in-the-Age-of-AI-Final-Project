# AI ASSISTANCE DISCLOSURE
# ChatGPT was used to brainstorm architecture, identify/verify public API endpoints,
# draft initial callback/data-cleaning patterns, styling, tests, and documentation.
# The team must review, run, edit, understand, and verify this file and its outputs
# against the linked official sources before submission or presentation.

from __future__ import annotations

import dash
from dash import Input, Output, callback, dcc, html, dash_table
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from services.tax_engine import rank_states
from services.bls_qcew import get_state_metrics as bls_states
from services.census_api import get_state_metrics as census_states, CensusAPIError
from utils.geography import FIPS_TO_NAME

dash.register_page(__name__, path='/rankings', name='Rankings')

METRICS = {
    'estimated_tax': 'Highest estimated state income tax',
    'effective_rate': 'Highest effective tax rate',
    'avg_wkly_wage': 'Highest average weekly wage',
    'job_growth': 'Fastest employment growth',
    'establishments': 'Most business establishments',
    'median_household_income': 'Highest median household income',
    'poverty_rate_low': 'Lowest poverty rate',
}

layout = html.Div([
    html.P('NATIONAL RANKINGS', className='eyebrow'),
    html.H2('Which states lead the country?'),
    html.Div([html.Label('Ranking'), dcc.Dropdown(id='ranking-metric', options=[{'label':v,'value':k} for k,v in METRICS.items()], value='estimated_tax', clearable=False)], className='control-block'),
    html.Div(id='ranking-note', className='status-note'),
    html.Div([
        html.Div([dcc.Graph(id='ranking-chart', config={'displayModeBar':False})], className='panel'),
        html.Div([dash_table.DataTable(id='ranking-table', page_size=15, style_table={'overflowX':'auto'}, style_cell={'padding':'10px','fontFamily':'Arial','textAlign':'left'}, style_header={'fontWeight':'700'})], className='panel')
    ], className='two-col')
])

@callback(
    Output('ranking-chart','figure'),
    Output('ranking-table','data'),
    Output('ranking-table','columns'),
    Output('ranking-note','children'),
    Input('ranking-metric','value'),
    Input('income-store','data'),
)
def update_rankings(metric, income_store):
    try:
        ascending = False
        if metric in {'estimated_tax','effective_rate'}:
            s = income_store or {'income':100000,'filing_status':'single'}
            df = rank_states(s.get('income',100000), s.get('filing_status','single'))[['state',metric]].copy()
            df = df.rename(columns={metric:'value'})
            note = f'2026 simplified state income-tax estimator at ${float(s.get("income",100000)):,.0f}.'
        elif metric in {'avg_wkly_wage','job_growth','establishments'}:
            b = bls_states().copy()
            b['state'] = b['state_fips'].map(FIPS_TO_NAME)
            col = {'avg_wkly_wage':'avg_wkly_wage','job_growth':'oty_month3_emplvl_pct_chg','establishments':'qtrly_estabs'}[metric]
            df = b[['state',col]].rename(columns={col:'value'}).dropna()
            note = 'BLS QCEW 2026 Q1.'
        else:
            c = census_states().copy()
            c['state'] = c['state_fips'].map(FIPS_TO_NAME)
            col = 'poverty_rate' if metric == 'poverty_rate_low' else 'median_household_income'
            df = c[['state',col]].rename(columns={col:'value'}).dropna()
            if metric == 'poverty_rate_low':
                ascending = True
            note = 'Census ACS 2024 5-year API.'
        df = df.dropna(subset=['state','value']).sort_values('value', ascending=ascending).head(15).reset_index(drop=True)
        df.insert(0,'rank',range(1,len(df)+1))
        plot_df = df.sort_values('value', ascending=not ascending)
        fig = px.bar(plot_df, x='value', y='state', orientation='h', labels={'value':METRICS[metric],'state':''})
        fig.update_layout(template='plotly_white', margin=dict(l=10,r=10,t=10,b=10), height=520)
        columns = [{'name':'Rank','id':'rank'},{'name':'State','id':'state'},{'name':'Value','id':'value','type':'numeric','format':{'specifier':',.2f'}}]
        return fig, df.to_dict('records'), columns, note
    except CensusAPIError as exc:
        fig = go.Figure().add_annotation(text=str(exc), x=.5, y=.5, showarrow=False)
        return fig, [], [], str(exc)
    except Exception as exc:
        fig = go.Figure().add_annotation(text=f'Ranking unavailable: {exc}', x=.5, y=.5, showarrow=False)
        return fig, [], [], f'Error: {exc}'
