# County map reliability

Click a state on the Interactive Map to load the keyless BLS average-weekly-wage
measure. Every county/county-equivalent in the bundled geography is shown with
white borders, and the API observations color the matching counties. Hover to
see a county name, or click to open its economic profile. **County boundaries —
no API needed** remains available as a separate map option.

Previously, county drawing required the economic API to succeed and only drew
features with returned observations. An API failure replaced the map with an
empty error figure, and unmatched counties could disappear.

The map now draws local geometry independently, scopes geometry to the selected
state, and overlays finite, matching observations. Missing observations retain
their slate-blue county shape and are not treated as zeros. API errors retain
the boundary view and county controls. Data coverage is reported as a matched
county count. The loading indicator also keeps the previous map visible.

A horizontal color scale leaves room for the state. White borders are applied to
both geography and data layers. County names come from the local GeoJSON, so they
do not require a second network request to BLS's area-title service.

The bundled Plotly/Census geography includes historical county-equivalent
boundaries (for example Connecticut's eight counties). Economic releases using
different county-equivalent codes may not match; the map reports missing data
rather than silently joining incompatible geographies. This change does not
change the geography vintage or invent new economic observations.

Regression tests cover all 50 states and D.C., partial/empty/invalid observations,
API errors, white borders and county names during profile failures.
