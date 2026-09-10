# AI ASSISTANCE DISCLOSURE
# ChatGPT helped isolate county geometry from API availability, normalize FIPS
# joins, preserve unmatched boundaries, and draft regression coverage. The team
# must review and understand the map and its data limitations.
"""Draw county geography independently of the availability of economic data."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from services.geojson import get_county_geojson, GeoJSONError


def county_boundaries(state_fips):
    features = [f for f in get_county_geojson()['features']
                if str(f.get('id', '')).startswith(state_fips)]
    if not features:
        raise GeoJSONError('No county boundaries are available for this state.')
    return {'type': 'FeatureCollection', 'features': features}


def county_figure(geojson, data=None, label='County boundaries'):
    """Keep every county clickable; overlay only finite, matching observations."""
    ids = [str(f['id']) for f in geojson['features']]
    names = []
    for feature in geojson['features']:
        properties = feature.get('properties', {})
        name = properties.get('NAME', feature['id'])
        kind = properties.get('LSAD', '')
        names.append(f'{name} {kind}'.strip())
    boundary_only = data is None
    fig = go.Figure(go.Choropleth(
        geojson=geojson, featureidkey='id', locationmode='geojson-id', locations=ids, z=[0] * len(ids),
        text=names, zmin=0, zmax=1, colorscale=[[0, '#526b87'], [1, '#526b87']],
        showscale=False, autocolorscale=False, marker_line_color='white', marker_line_width=1,
        hovertemplate='<b>%{text}</b><br>FIPS: %{location}<br>' +
                      ('Click for county details' if boundary_only else 'No matched data for this measure') + '<extra></extra>',
        name='County boundaries',
    ))
    matched = 0
    if data is not None and not data.empty:
        values = data.copy()
        values['fips'] = values['fips'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True).str.zfill(5)
        values['value'] = pd.to_numeric(values['value'], errors='coerce')
        values = values[values['fips'].isin(ids) & values['value'].notna() & ~values['value'].isin([float('inf'), float('-inf')])]
        values = values.drop_duplicates('fips')
        matched = len(values)
        if matched:
            # County names come from the same geography being displayed, even
            # when the optional area-title API is unavailable.
            county_names = dict(zip(ids, names))
            fig.add_trace(go.Choropleth(
                geojson=geojson, featureidkey='id', locationmode='geojson-id', locations=values['fips'], z=values['value'],
                text=values['fips'].map(county_names), colorscale='Magma',
                marker_line_color='white', marker_line_width=1,
                colorbar=dict(title=dict(text=label, side='top'), orientation='h',
                              x=.5, xanchor='center', y=-.06, len=.85, thickness=14),
                hovertemplate='<b>%{text}</b><br>FIPS: %{location}<br>' + label + ': %{z:,.2f}<extra></extra>',
                name=label,
            ))
    fig.update_geos(fitbounds='locations', visible=False, scope='world',
                    projection_type='mercator')
    fig.update_layout(margin=dict(l=12, r=12, t=12, b=65 if matched else 12),
                      paper_bgcolor='rgba(0,0,0,0)', height=650, showlegend=False)
    return fig, matched, len(ids)
