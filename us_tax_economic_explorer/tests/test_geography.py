# AI ASSISTANCE DISCLOSURE
# ChatGPT was used to brainstorm architecture, identify/verify public API endpoints,
# draft initial callback/data-cleaning patterns, styling, tests, and documentation.
# The team must review, run, edit, understand, and verify this file and its outputs
# against the linked official sources before submission or presentation.

from utils.geography import ABBR_TO_FIPS, FIPS_TO_NAME


def test_virginia_fips_mapping():
    assert ABBR_TO_FIPS['VA'] == '51'
    assert FIPS_TO_NAME['51'] == 'Virginia'
