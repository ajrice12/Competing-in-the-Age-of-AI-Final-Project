# AI ASSISTANCE DISCLOSURE
# ChatGPT was used to brainstorm architecture, identify/verify public API endpoints,
# draft initial callback/data-cleaning patterns, styling, tests, and documentation.
# The team must review, run, edit, understand, and verify this file and its outputs
# against the linked official sources before submission or presentation.

from services.tax_engine import estimate_state_tax, rank_states


def test_no_wage_income_tax_state():
    assert estimate_state_tax('Texas', 100000)['estimated_tax'] == 0
    assert estimate_state_tax('Washington', 100000)['estimated_tax'] == 0


def test_progressive_tax_increases_with_income():
    low = estimate_state_tax('Virginia', 50000)['estimated_tax']
    high = estimate_state_tax('Virginia', 150000)['estimated_tax']
    assert high > low > 0


def test_joint_filing_is_supported():
    result = estimate_state_tax('California', 150000, 'joint')
    assert result['gross_income'] == 150000
    assert result['estimated_tax'] >= 0


def test_rank_has_50_states():
    df = rank_states(100000)
    assert len(df) == 50
    assert set(['state','abbr','estimated_tax','effective_rate']).issubset(df.columns)
