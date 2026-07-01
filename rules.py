"""Domain-expert rules engine.

Each rule is a plain function: (row_or_group) -> dict | None.
A rule returns a structured flag when triggered, or None when it doesn't apply.
The AI layer (rag.py) only narrates flags this module already produced —
it never decides which thresholds matter.
"""

from dataclasses import dataclass


@dataclass
class Flag:
    rule_id: str
    channel: str
    campaign_name: str
    what_happened: str
    materiality: float  # spend-weighted impact, 0-1


# TODO: implement the starter rule set from the build spec:
# 1. fatigue (frequency > 4 + declining CTR)
# 2. search CTR underperformance (< 3%)
# 3. social CTR underperformance (< 0.9%)
# 4. CPA spike (> 20% WoW)
# 5. email list dilution
# 6. cross-channel acquisition-to-activation gap
# 7. programmatic viewability (< 50%)
# 8. search impression share drop (> 10pts WoW, flat spend)
# 9. unsubscribe spike (> 2x trailing average)
# 10. materiality threshold filter (> 15% of spend-weighted outcomes)

RULES = []


def run_rules(unified_df) -> list[Flag]:
    flags = []
    for rule in RULES:
        result = rule(unified_df)
        if result:
            flags.extend(result if isinstance(result, list) else [result])
    return sorted(flags, key=lambda f: f.materiality, reverse=True)
