"""
Email Templates — Phase 3 Follow-up Sequence
Plain-text only. No tracking pixels. No unsubscribe footer.
These are warm 1-to-1 follow-ups, not marketing blasts.

Lead types  : bulk_liquid | private_label | general
Sequence    : Day 1 → Day 3 → Day 7 → Day 14 (all on same Gmail thread)
Re-engage   : quarterly_reengage() — fires when stalled convo revives
"""
import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).parent.parent.parent      # CRM/
_CORE = _ROOT / "backend" / "core"
_SETUP = _ROOT / "backend" / "setup"
for _p in [str(_ROOT), str(_ROOT / "backend"), str(_CORE), str(_SETUP)]:
    if _p not in _sys.path:
        _sys.path.insert(0, _p)
del _sys, _Path, _ROOT, _CORE, _SETUP, _p


SENDER_NAME = "Aditi Rajput"
COMPANY     = "Your Company Name"       # ← update before go-live
WEBSITE     = "https://yourcompany.com" # ← update before go-live


# ── Helpers ───────────────────────────────────────────────────────────────────

def _first(props: dict) -> str:
    """Returns first name or 'there' as fallback."""
    return (props.get("firstname") or "there").strip()


# ── Day 1 — Initial intro (fires on expo_followup_date) ──────────────────────

def day1_bulk_liquid(props: dict) -> tuple[str, str]:
    first = _first(props)
    expo  = props.get("expo_name", "the expo")
    subject = f"Great meeting you at {expo}"
    body = (
        f"Hi {first},\n\n"
        f"It was great connecting with you at {expo}.\n\n"
        "I wanted to follow up on our conversation about bulk liquid solutions. "
        "We work with distributors and buyers across the region — "
        "whether you need 500L or 50,000L, we can match the volume with "
        "consistent quality and full documentation (COA, MSDS, Halal if needed).\n\n"
        "Would a quick 15-minute call this week make sense? "
        "Happy to work around your schedule.\n\n"
        f"Best,\n{SENDER_NAME}\n{COMPANY}\n{WEBSITE}"
    )
    return subject, body


def day1_private_label(props: dict) -> tuple[str, str]:
    first = _first(props)
    expo  = props.get("expo_name", "the expo")
    subject = f"Following up from {expo} — private label"
    body = (
        f"Hi {first},\n\n"
        f"Lovely meeting you at {expo}.\n\n"
        "I wanted to reach out about the private label opportunity we touched on. "
        "We handle the full process end-to-end — formulation, custom packaging, "
        "regulatory documentation, and production — with MOQs starting from 200 units.\n\n"
        "Are you free for a short call this week or next? "
        "I'd love to understand your vision better.\n\n"
        f"Warm regards,\n{SENDER_NAME}\n{COMPANY}\n{WEBSITE}"
    )
    return subject, body


def day1_general(props: dict) -> tuple[str, str]:
    first = _first(props)
    expo  = props.get("expo_name", "the expo")
    subject = f"Nice to meet you at {expo}"
    body = (
        f"Hi {first},\n\n"
        f"It was a pleasure meeting you at {expo}.\n\n"
        "I wanted to follow up and see how we might be able to work together. "
        "I'd love to learn more about what you're looking for and share "
        "how we've helped similar businesses.\n\n"
        "Would you be open to a brief call this week?\n\n"
        f"Best,\n{SENDER_NAME}\n{COMPANY}\n{WEBSITE}"
    )
    return subject, body


# ── Day 3 — Value-add follow-up ───────────────────────────────────────────────

def day3_bulk_liquid(props: dict) -> tuple[str, str]:
    first = _first(props)
    subject = "Re: bulk liquid sourcing — quick checklist"
    body = (
        f"Hi {first},\n\n"
        "Just checking in on my earlier email.\n\n"
        "I thought this might be useful — a short checklist our buyers use "
        "when evaluating bulk liquid suppliers:\n\n"
        "  - MOQs vs. your actual demand\n"
        "  - Lead times and buffer stock availability\n"
        "  - Quality certifications (ISO, GMP, Halal)\n"
        "  - Logistics to your destination port\n"
        "  - Payment terms flexibility\n\n"
        "Happy to walk you through how we tick each of these. "
        "Even a 10-minute call would be enough to see if there's a fit.\n\n"
        f"Best,\n{SENDER_NAME}\n{COMPANY}\n{WEBSITE}"
    )
    return subject, body


def day3_private_label(props: dict) -> tuple[str, str]:
    first = _first(props)
    subject = "Re: 3 things to know before launching a private label product"
    body = (
        f"Hi {first},\n\n"
        "Following up on my earlier email — a few things brands often overlook "
        "before launching a private label product:\n\n"
        "  1. Regulatory timelines — some markets need 3-6 months for approval. "
        "Starting early saves a lot of pain.\n"
        "  2. Packaging minimums — many manufacturers require large runs. "
        "We've structured our process to keep MOQs low.\n"
        "  3. Batch consistency — this is where quality control documentation "
        "becomes critical.\n\n"
        "We've navigated all of these for our existing partners. "
        "Happy to share more on a call — no pressure, just a conversation.\n\n"
        f"Warm regards,\n{SENDER_NAME}\n{COMPANY}\n{WEBSITE}"
    )
    return subject, body


def day3_general(props: dict) -> tuple[str, str]:
    first = _first(props)
    subject = "Re: following up — any questions?"
    body = (
        f"Hi {first},\n\n"
        "Just a quick follow-up to my earlier note.\n\n"
        "I know things get busy after an expo — if you have any questions "
        "or want to explore whether there's a fit, I'm happy to keep it "
        "low-key and informal. Even a 10-minute chat can help clarify things quickly.\n\n"
        "Let me know what works for you.\n\n"
        f"Best,\n{SENDER_NAME}\n{COMPANY}\n{WEBSITE}"
    )
    return subject, body


# ── Day 7 — Social proof ──────────────────────────────────────────────────────

def day7_bulk_liquid(props: dict) -> tuple[str, str]:
    first = _first(props)
    subject = "Re: how a regional distributor cut sourcing costs by 18%"
    body = (
        f"Hi {first},\n\n"
        "I wanted to share a quick example that might be relevant.\n\n"
        "One of our regional distribution partners was dealing with inconsistent "
        "quality and high per-unit costs from their previous supplier. "
        "After switching to us:\n\n"
        "  - Per-unit cost dropped 18% within the first two orders\n"
        "  - Lead time reduced from 6 weeks to 3 weeks\n"
        "  - Zero quality rejections in 12 months of supply\n\n"
        "I'm sharing this because the situation sounds similar to what you "
        "described at the expo. Would it be worth a 15-minute call?\n\n"
        f"Best,\n{SENDER_NAME}\n{COMPANY}\n{WEBSITE}"
    )
    return subject, body


def day7_private_label(props: dict) -> tuple[str, str]:
    first = _first(props)
    subject = "Re: from idea to shelf in 4 months"
    body = (
        f"Hi {first},\n\n"
        "I wanted to share a quick story.\n\n"
        "A client came to us with a product concept and a brand name — nothing else. "
        "Four months later they were on shelves in three countries:\n\n"
        "  - Week 1-2: Formulation finalised\n"
        "  - Week 3-6: Packaging design and production\n"
        "  - Week 7-10: Regulatory submissions (we handled the paperwork)\n"
        "  - Week 11-16: First production run, QC, and shipping\n\n"
        "This is exactly what we do. Are you free for a call this week?\n\n"
        f"Warm regards,\n{SENDER_NAME}\n{COMPANY}\n{WEBSITE}"
    )
    return subject, body


def day7_general(props: dict) -> tuple[str, str]:
    first = _first(props)
    subject = "Re: one more thought"
    body = (
        f"Hi {first},\n\n"
        "I've reached out a couple of times and I don't want to be a nuisance — "
        "so this will be my last check-in for a while.\n\n"
        "If the timing isn't right, that's completely fine. "
        "If there's anything I can answer, or if you'd like to revisit this "
        "in a few months, just reply to this email and I'll pick it up immediately.\n\n"
        f"Wishing you all the best,\n{SENDER_NAME}\n{COMPANY}\n{WEBSITE}"
    )
    return subject, body


# ── Day 14 — Last nudge ───────────────────────────────────────────────────────

def day14_bulk_liquid(props: dict) -> tuple[str, str]:
    first = _first(props)
    subject = "Re: closing the loop on bulk liquid sourcing"
    body = (
        f"Hi {first},\n\n"
        "I've followed up a few times and I don't want to keep filling your inbox "
        "if the timing isn't right.\n\n"
        "This will be my last email for now — but if bulk liquid sourcing "
        "becomes a priority down the road, just reply here and I'll get back to you right away.\n\n"
        f"Take care,\n{SENDER_NAME}\n{COMPANY}\n{WEBSITE}"
    )
    return subject, body


def day14_private_label(props: dict) -> tuple[str, str]:
    first = _first(props)
    subject = "Re: closing the loop — private label"
    body = (
        f"Hi {first},\n\n"
        "I've sent a few emails over the past two weeks and I want to respect your time — "
        "so this will be my last follow-up for now.\n\n"
        "If private label manufacturing becomes relevant for you down the road, "
        "please don't hesitate to reach out. We'll be here.\n\n"
        f"Wishing you the best,\n{SENDER_NAME}\n{COMPANY}\n{WEBSITE}"
    )
    return subject, body


def day14_general(props: dict) -> tuple[str, str]:
    first = _first(props)
    subject = "Re: closing the loop"
    body = (
        f"Hi {first},\n\n"
        "Just closing the loop on my previous emails.\n\n"
        "If the timing wasn't right or you went in a different direction, "
        "no worries at all — I completely understand.\n\n"
        "If things change and you'd like to reconnect, just reply here "
        "and I'll pick it up straight away.\n\n"
        f"All the best,\n{SENDER_NAME}\n{COMPANY}\n{WEBSITE}"
    )
    return subject, body


# ── Stalled re-engagement (fires after STALLED_DAYS of silence post-reply) ────

def stalled_reengage(props: dict) -> tuple[str, str]:
    first = _first(props)
    subject = "Re: checking in"
    body = (
        f"Hi {first},\n\n"
        "It's been a little while since we last spoke — I hope things are going well.\n\n"
        "I wanted to check in and see if anything has changed on your end, "
        "or if there's anything I can help with.\n\n"
        "No pressure at all — just wanted to stay in touch.\n\n"
        f"Best,\n{SENDER_NAME}\n{COMPANY}\n{WEBSITE}"
    )
    return subject, body


# ── Template dispatcher ───────────────────────────────────────────────────────

_TEMPLATE_MAP: dict[tuple, object] = {
    (1,  "bulk"):    day1_bulk_liquid,
    (1,  "private"): day1_private_label,
    (1,  "general"): day1_general,
    (3,  "bulk"):    day3_bulk_liquid,
    (3,  "private"): day3_private_label,
    (3,  "general"): day3_general,
    (7,  "bulk"):    day7_bulk_liquid,
    (7,  "private"): day7_private_label,
    (7,  "general"): day7_general,
    (14, "bulk"):    day14_bulk_liquid,
    (14, "private"): day14_private_label,
    (14, "general"): day14_general,
}

SEQUENCE_DAYS = [1, 3, 7, 14]


def get_template(day: int, lead_type: str, props: dict) -> tuple[str, str]:
    """
    Returns (subject, body_plain_text) for the given sequence day and lead type.
    Falls back to 'general' if lead_type doesn't match bulk/private.

    Args:
        day       : 1, 3, 7, or 14
        lead_type : value from HubSpot lead_type property
        props     : dict of HubSpot contact properties

    Returns:
        (subject: str, body: str)  — plain text, no HTML
    """
    lt = (lead_type or "").lower()
    if "bulk" in lt:
        bucket = "bulk"
    elif "private" in lt:
        bucket = "private"
    else:
        bucket = "general"

    fn = _TEMPLATE_MAP.get((day, bucket))
    if fn is None:
        raise ValueError(f"No template for day={day}, lead_type='{lead_type}'")
    return fn(props)
