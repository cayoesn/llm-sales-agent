from typing import Any

from pydantic import BaseModel, Field


class RecommendedProduct(BaseModel):
    product_name: str
    price: float
    reason_for_recommendation: str
    discount_applicable: bool = False


class ConversationalSalesResponse(BaseModel):
    """Pydantic V2 schema guaranteeing structured output from the Sales Agent."""

    message: str = Field(
        description="Friendly natural language response for the customer."
    )
    intent_detected: str = Field(description="Detected user intent.")
    recommended_products: list[RecommendedProduct] = Field(
        default_factory=list,
        description="List of products recommended via Graph-RAG.",
    )
    negotiation_applied: bool = Field(
        default=False,
        description="Indicates whether discount negotiation or calculation occurred.",
    )
    next_recommended_action: str | None = Field(
        default=None,
        description="Suggested next step for the customer.",
    )


class SalesAgentOutputValidator:
    """Structured Output Validator and Formatter for the Sales Agent."""

    @staticmethod
    def validate_or_fallback(
        raw_response: dict[str, Any] | str,
    ) -> ConversationalSalesResponse:
        if isinstance(raw_response, dict):
            try:
                return ConversationalSalesResponse(**raw_response)
            except Exception:
                pass

        text = str(raw_response)
        return ConversationalSalesResponse(
            message=text,
            intent_detected="general_chat",
            recommended_products=[],
            negotiation_applied=False,
            next_recommended_action="Offer assistance with adding items to the cart.",
        )
