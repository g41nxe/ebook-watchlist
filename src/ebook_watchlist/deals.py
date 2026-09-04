"""The two-tier deal rule (ADR 5).

The distinction the reader actually cares about: *cheap outright* needs no
argument, but a mid-range price only counts as news if it genuinely came down.
A standing 9,99 € is not a deal no matter how long you watch it.
"""

from __future__ import annotations

from .config import Profile
from .models import Observation

STRONG_DEAL = "Strong Deal"
DEAL = "Deal"


def is_strong_deal(price_cents: int | None, profile: Profile) -> bool:
    """Cheap enough to need no argument — but not free.

    Zero is not the best bargain on the shelf, it is filler: every free title in
    a real Run was a bundle or a promotional giveaway (ADR 19). Badging those as
    the strongest deal on the page was the surest way to make the badge
    meaningless.
    """
    if price_cents is None or price_cents <= 0:
        return False
    return price_cents < profile.strong_deal_max_cents


def _discounted_from(price_cents: int, reference_cents: int | None, profile: Profile) -> bool:
    if not reference_cents or reference_cents <= price_cents:
        return False
    drop_pct = (reference_cents - price_cents) * 100 / reference_cents
    return drop_pct >= profile.min_discount_pct


def is_deal(observation: Observation, previous: Observation | None, profile: Profile) -> bool:
    """A genuine discount inside the mid price band."""
    price = observation.price_cents
    if price is None:
        return False
    if not (profile.strong_deal_max_cents <= price < profile.deal_max_cents):
        return False

    # Two independent kinds of evidence. beam-shop never renders a struck price
    # (German fixed-book-price law), so there it is always the second one.
    if _discounted_from(price, observation.original_price_cents, profile):
        return True
    return _discounted_from(price, previous.price_cents if previous else None, profile)


def deal_flags(
    observation: Observation, previous: Observation | None, profile: Profile
) -> tuple[str, ...]:
    if is_strong_deal(observation.price_cents, profile):
        return (STRONG_DEAL,)
    if is_deal(observation, previous, profile):
        return (DEAL,)
    return ()
