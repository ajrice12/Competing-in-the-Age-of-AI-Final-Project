# AI ASSISTANCE DISCLOSURE
# ChatGPT was used to brainstorm architecture, identify/verify public API endpoints,
# draft initial callback/data-cleaning patterns, styling, tests, and documentation.
# The team must review, run, edit, understand, and verify this file and its outputs
# against the linked official sources before submission or presentation.

STATE_META = {
    'Alabama': ('AL','01'), 'Alaska': ('AK','02'), 'Arizona': ('AZ','04'), 'Arkansas': ('AR','05'),
    'California': ('CA','06'), 'Colorado': ('CO','08'), 'Connecticut': ('CT','09'), 'Delaware': ('DE','10'),
    'District of Columbia': ('DC','11'), 'Florida': ('FL','12'), 'Georgia': ('GA','13'), 'Hawaii': ('HI','15'),
    'Idaho': ('ID','16'), 'Illinois': ('IL','17'), 'Indiana': ('IN','18'), 'Iowa': ('IA','19'),
    'Kansas': ('KS','20'), 'Kentucky': ('KY','21'), 'Louisiana': ('LA','22'), 'Maine': ('ME','23'),
    'Maryland': ('MD','24'), 'Massachusetts': ('MA','25'), 'Michigan': ('MI','26'), 'Minnesota': ('MN','27'),
    'Mississippi': ('MS','28'), 'Missouri': ('MO','29'), 'Montana': ('MT','30'), 'Nebraska': ('NE','31'),
    'Nevada': ('NV','32'), 'New Hampshire': ('NH','33'), 'New Jersey': ('NJ','34'), 'New Mexico': ('NM','35'),
    'New York': ('NY','36'), 'North Carolina': ('NC','37'), 'North Dakota': ('ND','38'), 'Ohio': ('OH','39'),
    'Oklahoma': ('OK','40'), 'Oregon': ('OR','41'), 'Pennsylvania': ('PA','42'), 'Rhode Island': ('RI','44'),
    'South Carolina': ('SC','45'), 'South Dakota': ('SD','46'), 'Tennessee': ('TN','47'), 'Texas': ('TX','48'),
    'Utah': ('UT','49'), 'Vermont': ('VT','50'), 'Virginia': ('VA','51'), 'Washington': ('WA','53'),
    'West Virginia': ('WV','54'), 'Wisconsin': ('WI','55'), 'Wyoming': ('WY','56'),
}

NAME_TO_ABBR = {name: meta[0] for name, meta in STATE_META.items()}
ABBR_TO_NAME = {meta[0]: name for name, meta in STATE_META.items()}
NAME_TO_FIPS = {name: meta[1] for name, meta in STATE_META.items()}
FIPS_TO_NAME = {meta[1]: name for name, meta in STATE_META.items()}
ABBR_TO_FIPS = {meta[0]: meta[1] for name, meta in STATE_META.items()}
FIPS_TO_ABBR = {meta[1]: meta[0] for name, meta in STATE_META.items()}

CONTIGUOUS_STATE_ABBRS = [abbr for abbr in ABBR_TO_NAME if abbr not in {'AK','HI','DC'}]
