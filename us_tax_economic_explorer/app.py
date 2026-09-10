# AI ASSISTANCE DISCLOSURE
# ChatGPT was used to brainstorm architecture, identify/verify public API endpoints,
# draft initial callback/data-cleaning patterns, styling, tests, and documentation.


from __future__ import annotations

import dash
from dash import Dash, dcc, html, page_container
from dotenv import load_dotenv

# Load local secrets and settings before any page imports an API service.
load_dotenv()

app = Dash(
    __name__,
    use_pages=True,
    suppress_callback_exceptions=True,
    title='U.S. Tax & Economic Explorer',
    update_title='Updating…',
)
server = app.server

# Dash discovers the files in pages/; this list controls the visible menu order.
NAV_ITEMS = [
    ('Home / Tax Explorer', '/'),
    ('Interactive Map', '/map'),
    ('Compare States', '/compare'),
    ('Rankings', '/rankings'),
]

app.layout = html.Div([
    # Keep the user's income scenario when they move between app pages.
    dcc.Store(id='income-store', storage_type='local', data={'income': 100000, 'filing_status': 'single'}),
    html.Header([
        html.Div([
            html.Div('US', className='brand-mark'),
            html.Div([
                html.H1('Tax & Economic Explorer', className='brand-title'),
                html.P('Live-ish government economic data with state → county drill-down', className='brand-subtitle'),
            ]),
        ], className='brand-row'),
        html.Nav([
            dcc.Link(label, href=href, className='nav-link') for label, href in NAV_ITEMS
        ], className='nav-links'),
    ], className='site-header'),
    html.Main(page_container, className='page-shell'),
    html.Footer([
        html.Span('Educational analytics only — simplified tax estimates are not tax advice.'),
        html.Span(' Data sources: BLS QCEW, Census ACS, optional BEA Regional API.'),
    ], className='site-footer')
])

if __name__ == '__main__':
    app.run(debug=True)
