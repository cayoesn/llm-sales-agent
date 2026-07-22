from typing import Any
from pydantic import BaseModel, Field


class RecommendedProduct(BaseModel):
    product_name: str
    price: float
    reason_for_recommendation: str
    discount_applicable: bool = False


class ConversationalSalesResponse(BaseModel):
    """Schema Pydantic V2 para garantia de saída estruturada do Agente de Vendas."""
    message: str = Field(description="Resposta amigável em linguagem natural para o cliente.")
    intent_detected: str = Field(description="Intenção identificada do usuário.")
    recommended_products: list[RecommendedProduct] = Field(default_factory=list, description="Lista de produtos recomendados via Graph-RAG.")
    negotiation_applied: bool = Field(default=False, description="Indica se houve negociação ou cálculo de desconto.")
    next_recommended_action: str | None = Field(default=None, description="Ação sugerida para o próximo passo do cliente.")


class SalesAgentOutputValidator:
    """Validador e Formatador de Saída Estruturada para o Agente de Vendas."""

    @staticmethod
    def validate_or_fallback(raw_response: dict[str, Any] | str) -> ConversationalSalesResponse:
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
            next_recommended_action="Oferecer ajuda para adicionar itens ao carrinho."
        )
