# AI ASSISTANCE DISCLOSURE
# ChatGPT was used to brainstorm architecture, identify/verify public API endpoints,
# draft initial callback/data-cleaning patterns, styling, tests, and documentation.
# The team must review, run, edit, understand, and verify this file and its outputs
# against the linked official sources before submission or presentation.

"""
Simplified 2026 state individual income-tax estimator.

Source basis: Tax Foundation, "State Individual Income Tax Rates and Brackets, 2026"
(as of Jan. 1, 2026; table updated during 2026).

Important: this is an educational estimator, not tax advice. It intentionally excludes
local income taxes, most credits, itemized deductions, special phaseouts, capital-gains
rules, and state-specific adjustments that require a full tax return.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple
import pandas as pd

from utils.geography import NAME_TO_ABBR

Bracket = Tuple[float, float]  # (threshold, rate)

@dataclass(frozen=True)
class FilingRule:
    brackets: List[Bracket]
    standard_deduction: float = 0.0
    personal_exemption: float = 0.0

@dataclass(frozen=True)
class StateRule:
    single: FilingRule
    joint: FilingRule
    note: str = ""


def fr(brackets, sd=0, pe=0):
    return FilingRule(brackets=brackets, standard_deduction=sd, personal_exemption=pe)

# Thresholds are taxable-income thresholds. Dollar exemptions that operate like deductions
# are included; tax credits and complicated phaseouts are intentionally excluded.
R: Dict[str, StateRule] = {
    'Alabama': StateRule(fr([(0,.02),(500,.04),(3000,.05)],3000,1500), fr([(0,.02),(1000,.04),(6000,.05)],8500,3000)),
    'Alaska': StateRule(fr([]), fr([]), 'No individual wage income tax.'),
    'Arizona': StateRule(fr([(0,.025)],8350), fr([(0,.025)],16700)),
    'Arkansas': StateRule(fr([(0,.02),(4600,.039)],2470), fr([(0,.02),(4600,.039)],4940)),
    'California': StateRule(fr([(0,.01),(11079,.02),(26264,.04),(41452,.06),(57542,.08),(72724,.093),(371479,.103),(445771,.113),(742953,.123),(1000000,.133)],5540), fr([(0,.01),(22158,.02),(52528,.04),(82904,.06),(115084,.08),(145448,.093),(742958,.103),(891542,.113),(1000000,.123),(1485906,.133)],11080)),
    'Colorado': StateRule(fr([(0,.044)],16100), fr([(0,.044)],32200)),
    'Connecticut': StateRule(fr([(0,.02),(10000,.045),(50000,.055),(100000,.06),(200000,.065),(250000,.069),(500000,.0699)],0,15000), fr([(0,.02),(20000,.045),(100000,.055),(200000,.06),(400000,.065),(500000,.069),(1000000,.0699)],0,24000)),
    'Delaware': StateRule(fr([(2000,.022),(5000,.039),(10000,.048),(20000,.052),(25000,.0555),(60000,.066)],3250), fr([(2000,.022),(5000,.039),(10000,.048),(20000,.052),(25000,.0555),(60000,.066)],6500)),
    'Florida': StateRule(fr([]), fr([]), 'No individual wage income tax.'),
    'Georgia': StateRule(fr([(0,.0519)],12000), fr([(0,.0519)],24000)),
    'Hawaii': StateRule(fr([(0,.014),(9600,.032),(14400,.055),(19200,.064),(24000,.068),(36000,.072),(48000,.076),(125000,.079),(175000,.0825),(225000,.09),(275000,.10),(325000,.11)],4400,1144), fr([(0,.014),(19200,.032),(28800,.055),(38400,.064),(48000,.068),(72000,.072),(96000,.076),(250000,.079),(350000,.0825),(450000,.09),(550000,.10),(650000,.11)],8800,2288)),
    'Idaho': StateRule(fr([(4811,.053)],16100), fr([(9622,.053)],32200)),
    'Illinois': StateRule(fr([(0,.0495)],0,2925), fr([(0,.0495)],0,5850)),
    'Indiana': StateRule(fr([(0,.0295)],0,1000), fr([(0,.0295)],0,2000)),
    'Iowa': StateRule(fr([(0,.038)],16100), fr([(0,.038)],32200)),
    'Kansas': StateRule(fr([(0,.052),(23000,.0558)],3605,9160), fr([(0,.052),(46000,.0558)],8240,18320)),
    'Kentucky': StateRule(fr([(0,.035)],3360), fr([(0,.035)],3360)),
    'Louisiana': StateRule(fr([(0,.03)],12875), fr([(0,.03)],25750)),
    'Maine': StateRule(fr([(0,.058),(27399,.0675),(64849,.0715)],8350,5300), fr([(0,.058),(54849,.0675),(129749,.0715)],16700,10600)),
    'Maryland': StateRule(fr([(0,.02),(1000,.03),(2000,.04),(3000,.0475),(100000,.05),(125000,.0525),(150000,.055),(250000,.0575),(500000,.0625),(1000000,.065)],3350,3200), fr([(0,.02),(1000,.03),(2000,.04),(3000,.0475),(150000,.05),(175000,.0525),(225000,.055),(300000,.0575),(600000,.0625),(1200000,.065)],6700,6400), 'Local county income taxes excluded.'),
    'Massachusetts': StateRule(fr([(0,.05),(1083150,.09)],0,4400), fr([(0,.05),(1083150,.09)],0,8800)),
    'Michigan': StateRule(fr([(0,.0425)],0,5900), fr([(0,.0425)],0,11800)),
    'Minnesota': StateRule(fr([(0,.0535),(33310,.068),(109430,.0785),(203150,.0985)],15300), fr([(0,.0535),(48700,.068),(193480,.0785),(337930,.0985)],30600)),
    'Mississippi': StateRule(fr([(10000,.04)],2300,6000), fr([(10000,.04)],4600,12000)),
    'Missouri': StateRule(fr([(1348,.02),(2696,.025),(4044,.03),(5392,.035),(6740,.04),(8088,.045),(9436,.047)],16100), fr([(1348,.02),(2696,.025),(4044,.03),(5392,.035),(6740,.04),(8088,.045),(9436,.047)],32200)),
    'Montana': StateRule(fr([(0,.047),(47500,.0565)],16100), fr([(0,.047),(95000,.0565)],32200)),
    'Nebraska': StateRule(fr([(0,.0246),(4130,.0351),(24760,.0455)],8850), fr([(0,.0246),(8250,.0351),(49530,.0455)],17700)),
    'Nevada': StateRule(fr([]), fr([]), 'No individual wage income tax.'),
    'New Hampshire': StateRule(fr([]), fr([]), 'No individual wage income tax.'),
    'New Jersey': StateRule(fr([(0,.014),(20000,.0175),(35000,.035),(40000,.0553),(75000,.0637),(500000,.0897),(1000000,.1075)],0,1000), fr([(0,.014),(20000,.0175),(50000,.0245),(70000,.035),(80000,.0553),(150000,.0637),(500000,.0897),(1000000,.1075)],0,2000)),
    'New Mexico': StateRule(fr([(0,.015),(5500,.032),(16500,.043),(33500,.047),(66500,.049),(210000,.059)],16100), fr([(0,.015),(8000,.032),(25000,.043),(50000,.047),(100000,.049),(315000,.059)],32200)),
    'New York': StateRule(fr([(0,.039),(8500,.044),(11700,.0515),(13900,.054),(80650,.059),(215400,.0685),(1077550,.0965),(5000000,.103),(25000000,.109)],8000), fr([(0,.039),(17150,.044),(23600,.0515),(27900,.054),(161550,.059),(323200,.0685),(2155350,.0965),(5000000,.103),(25000000,.109)],16050), 'NYC/Yonkers local income taxes excluded.'),
    'North Carolina': StateRule(fr([(0,.0399)],12750), fr([(0,.0399)],25500)),
    'North Dakota': StateRule(fr([(48475,.0195),(244825,.025)],16100), fr([(80975,.0195),(298075,.025)],32200)),
    'Ohio': StateRule(fr([(26050,.0275)],0,2400), fr([(26050,.0275)],0,4800), 'Municipal income taxes excluded.'),
    'Oklahoma': StateRule(fr([(3750,.025),(4900,.035),(7200,.045)],6350,1000), fr([(7500,.025),(9800,.035),(14400,.045)],12700,2000)),
    'Oregon': StateRule(fr([(0,.0475),(4550,.0675),(11400,.0875),(125000,.099)],2910), fr([(0,.0475),(9100,.0675),(22800,.0875),(250000,.099)],5820), 'Some local taxes excluded.'),
    'Pennsylvania': StateRule(fr([(0,.0307)]), fr([(0,.0307)]), 'Local earned-income taxes excluded.'),
    'Rhode Island': StateRule(fr([(0,.0375),(82050,.0475),(186450,.0599)],11200,5250), fr([(0,.0375),(82050,.0475),(186450,.0599)],22400,10500)),
    'South Carolina': StateRule(fr([(0,0),(3640,.03),(18230,.06)],8350), fr([(0,0),(3640,.03),(18230,.06)],16700)),
    'South Dakota': StateRule(fr([]), fr([]), 'No individual wage income tax.'),
    'Tennessee': StateRule(fr([]), fr([]), 'No individual wage income tax.'),
    'Texas': StateRule(fr([]), fr([]), 'No individual wage income tax.'),
    'Utah': StateRule(fr([(0,.045)]), fr([(0,.045)]), 'Utah credits are not modeled in this simplified estimator.'),
    'Vermont': StateRule(fr([(0,.0335),(49400,.066),(119700,.076),(249700,.0875)],7650,5300), fr([(0,.0335),(82500,.066),(199450,.076),(304000,.0875)],15300,10600)),
    'Virginia': StateRule(fr([(0,.02),(3000,.03),(5000,.05),(17000,.0575)],8750,930), fr([(0,.02),(3000,.03),(5000,.05),(17000,.0575)],17500,1860)),
    'Washington': StateRule(fr([]), fr([]), 'Washington taxes qualifying capital gains, not wage income.'),
    'West Virginia': StateRule(fr([(0,.0222),(10000,.0296),(25000,.0333),(40000,.0444),(60000,.0482)],0,2000), fr([(0,.0222),(10000,.0296),(25000,.0333),(40000,.0444),(60000,.0482)],0,4000)),
    'Wisconsin': StateRule(fr([(0,.035),(15110,.044),(51950,.053),(332720,.0765)],13960,700), fr([(0,.035),(20150,.044),(69260,.053),(443630,.0765)],25840,1400)),
    'Wyoming': StateRule(fr([]), fr([]), 'No individual wage income tax.'),
    'District of Columbia': StateRule(fr([(0,.04),(10000,.06),(40000,.065),(60000,.085),(250000,.0925),(500000,.0975),(1000000,.1075)],16100), fr([(0,.04),(10000,.06),(40000,.065),(60000,.085),(250000,.0925),(500000,.0975),(1000000,.1075)],32200)),
}


def _progressive_tax(taxable_income: float, brackets: List[Bracket]) -> float:
    if taxable_income <= 0 or not brackets:
        return 0.0
    brackets = sorted(brackets, key=lambda x: x[0])
    total = 0.0
    for i, (threshold, rate) in enumerate(brackets):
        if taxable_income <= threshold:
            break
        upper = brackets[i + 1][0] if i + 1 < len(brackets) else taxable_income
        amount = min(taxable_income, upper) - threshold
        if amount > 0:
            total += amount * rate
    return max(total, 0.0)


def estimate_state_tax(state: str, gross_income: float, filing_status: str = 'single') -> dict:
    if state not in R:
        raise KeyError(f'Unknown state: {state}')
    income = max(float(gross_income or 0), 0.0)
    rule = R[state]
    filing = rule.joint if filing_status == 'joint' else rule.single
    taxable = max(income - filing.standard_deduction - filing.personal_exemption, 0.0)
    tax = _progressive_tax(taxable, filing.brackets)
    return {
        'state': state,
        'abbr': NAME_TO_ABBR[state],
        'gross_income': income,
        'taxable_income_est': taxable,
        'estimated_tax': tax,
        'effective_rate': (tax / income * 100) if income > 0 else 0.0,
        'note': rule.note,
    }


def rank_states(gross_income: float, filing_status: str = 'single') -> pd.DataFrame:
    rows = [estimate_state_tax(state, gross_income, filing_status) for state in R if state != 'District of Columbia']
    return pd.DataFrame(rows).sort_values(['estimated_tax','state'], ascending=[False, True]).reset_index(drop=True)
