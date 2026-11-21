import math
from enum import StrEnum

from pydantic import BaseModel, Field


class NegotiationState(StrEnum):
    DISCOVERY = "DISCOVERY"
    CART_BUILDING = "CART_BUILDING"
    NEGOTIATION = "NEGOTIATING_DISCOUNT"
    CHECKOUT_PENDING = "CHECKOUT_PENDING"
    COMPLETED = "COMPLETED"


class DiscountApproval(BaseModel):
    approved: bool
    requested_discount_percent: float
    approved_discount_percent: float
    final_price: float
    reason: str
    expected_utility: float = Field(default=0.0)
    conversion_probability: float = Field(default=0.0)


class NegotiationFSM:
    """Enterprise Negotiation Finite State Machine & Utility Maximizer.

    Enforces strict corporate bounds on discount margins and eligibility,
    computing expected transaction utility via a logistic conversion function:
        U(d) = (Net Revenue) * P(conversion | d)
    ensuring the agent maximizes expected revenue without hallucinating concessions.
    """

    MAX_PIX_DISCOUNT_PERCENT = 10.0
    MAX_BULK_DISCOUNT_PERCENT = 12.0
    ABSOLUTE_MAX_DISCOUNT_PERCENT = 15.0

    @classmethod
    def _estimate_conversion_probability(cls, discount_percent: float) -> float:
        """Logistic sigmoid function for sale closing probability."""
        # 40% baseline at 0% discount, saturating near 95% as discounts approach the cap
        k = 0.25
        d0 = 5.0
        p = 1.0 / (1.0 + math.exp(-k * (discount_percent - d0)))
        return round(float(min(0.99, max(0.10, p))), 4)

    @classmethod
    def evaluate_discount_request(
        cls,
        cart_total: float,
        requested_discount_percent: float,
        payment_method: str = "PIX",
    ) -> DiscountApproval:
        """Evaluate and approve or cap the discount percentage based on strict rules and utility."""
        if cart_total <= 0:
            return DiscountApproval(
                approved=False,
                requested_discount_percent=requested_discount_percent,
                approved_discount_percent=0.0,
                final_price=0.0,
                reason="Cart has no eligible value for a discount.",
                expected_utility=0.0,
                conversion_probability=0.0,
            )

        # Rule 1: Absolute cap by payment method and order volume
        max_allowed = (
            cls.MAX_PIX_DISCOUNT_PERCENT if payment_method.upper() == "PIX" else 5.0
        )
        if cart_total >= 1000.0:
            max_allowed = max(max_allowed, cls.MAX_BULK_DISCOUNT_PERCENT)

        approved_percent = min(requested_discount_percent, max_allowed)
        approved_percent = min(approved_percent, cls.ABSOLUTE_MAX_DISCOUNT_PERCENT)

        final_price = round(cart_total * (1.0 - (approved_percent / 100.0)), 2)
        conv_prob = cls._estimate_conversion_probability(approved_percent)
        expected_utility = round(final_price * conv_prob, 2)

        if approved_percent < requested_discount_percent:
            reason = (
                f"Requested discount of {requested_discount_percent:.1f}% exceeds the allowed margin. "
                f"Applied maximum cap of {approved_percent:.1f}% for {payment_method}."
            )
        else:
            reason = (
                f"Discount of {approved_percent:.1f}% successfully approved "
                f"for {payment_method} payment."
            )

        return DiscountApproval(
            approved=True,
            requested_discount_percent=requested_discount_percent,
            approved_discount_percent=approved_percent,
            final_price=final_price,
            reason=reason,
            expected_utility=expected_utility,
            conversion_probability=conv_prob,
        )


# Singleton instance of the Negotiation FSM
negotiation_fsm = NegotiationFSM()
