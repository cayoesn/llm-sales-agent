from enum import StrEnum
from typing import Any
from pydantic import BaseModel


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


class NegotiationFSM:
    """Enterprise Negotiation Finite State Machine (Non-Hallucination Guardrail).
    
    Impõe limites corporativos estritos sobre margens de desconto e elegibilidade,
    garantindo que o modelo não conceda descontos abusivos ou alucinados.
    """

    MAX_PIX_DISCOUNT_PERCENT = 10.0
    MAX_BULK_DISCOUNT_PERCENT = 12.0
    ABSOLUTE_MAX_DISCOUNT_PERCENT = 15.0

    @classmethod
    def evaluate_discount_request(
        self,
        cart_total: float,
        requested_discount_percent: float,
        payment_method: str = "PIX",
    ) -> DiscountApproval:
        """Avalia e aprova ou limita a porcentagem de desconto com base em regras estritas."""
        if cart_total <= 0:
            return DiscountApproval(
                approved=False,
                requested_discount_percent=requested_discount_percent,
                approved_discount_percent=0.0,
                final_price=0.0,
                reason="Carrinho sem valor elegível para desconto."
            )

        # Regra 1: Teto absoluto
        max_allowed = self.MAX_PIX_DISCOUNT_PERCENT if payment_method.upper() == "PIX" else 5.0
        if cart_total >= 1000.0:
            max_allowed = max(max_allowed, self.MAX_BULK_DISCOUNT_PERCENT)

        approved_percent = min(requested_discount_percent, max_allowed)
        approved_percent = min(approved_percent, self.ABSOLUTE_MAX_DISCOUNT_PERCENT)

        final_price = round(cart_total * (1.0 - (approved_percent / 100.0)), 2)

        if approved_percent < requested_discount_percent:
            reason = f"Desconto solicitado de {requested_discount_percent:.1f}% excede a margem permitida. Aplicado teto máximo de {approved_percent:.1f}% para {payment_method}."
        else:
            reason = f"Desconto de {approved_percent:.1f}% aprovado com sucesso para pagamento via {payment_method}."

        return DiscountApproval(
            approved=True,
            requested_discount_percent=requested_discount_percent,
            approved_discount_percent=approved_percent,
            final_price=final_price,
            reason=reason,
        )


# Instância Singleton da FSM de Negociação
negotiation_fsm = NegotiationFSM()
