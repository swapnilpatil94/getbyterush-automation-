#!/usr/bin/env python3
"""GetByteRush daily posting slots.

Five fixed times/day (IST), each targeting a specific content-mix
category so the day reads as a deliberate schedule rather than five
random picks. Generation is triggered ~45 minutes before each public
time, giving slack for GitHub Actions cron jitter (schedule triggers are
best-effort, not exact) and for the render -> QA -> Telegram chain to
finish before the post is due.

cron_utc is IST minus 5:30, for reference / the workflow file — this
module itself has no timezone logic, it's just the category routing.
"""

SLOTS = {
    "morning": {
        "categories": ["EVERGREEN_VALUE"],
        "label": "Morning discovery",
        "public_time_ist": "08:00",
        "generate_time_ist": "07:15",
        "cron_utc": "45 1 * * *",
    },
    "midmorning": {
        "categories": ["EXPERIMENT", "PRODUCT_TOOL"],
        "label": "Curiosity + saves",
        "public_time_ist": "11:30",
        "generate_time_ist": "10:45",
        "cron_utc": "15 5 * * *",
    },
    "afternoon": {
        "categories": ["LAST_24H"],
        "label": "Freshness",
        "public_time_ist": "14:30",
        "generate_time_ist": "13:45",
        "cron_utc": "15 8 * * *",
    },
    "evening": {
        "categories": ["CURIOSITY", "INTERNET_HUMAN_TECH_BEHAVIOR"],
        "label": "High-attention window",
        "public_time_ist": "18:30",
        "generate_time_ist": "17:45",
        "cron_utc": "15 12 * * *",
    },
    "night": {
        "categories": None,  # any category — best remaining post of the day
        "label": "Maximum push",
        "public_time_ist": "21:00",
        "generate_time_ist": "20:15",
        "cron_utc": "45 14 * * *",
    },
}

SLOT_ORDER = ["morning", "midmorning", "afternoon", "evening", "night"]


def slot_for_cron(cron_expr):
    for name, slot in SLOTS.items():
        if slot["cron_utc"] == cron_expr:
            return name
    return None
