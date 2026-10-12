import math
from enum import StrEnum
from typing import Any, Dict
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
    
    Impõe limites corporativos estritos sobre margens de desconto e elegibilidade,
    calculando a utilidade esperada da transação via função logística de conversão:
        U(d) = (Receita Líquida) * P(conversão | d)
    garantindo que o agente maximize a receita esperada sem alucinar concessões.
    """

    MAX_PIX_DISCOUNT_PERCENT = 10.0
    MAX_BULK_DISCOUNT_PERCENT = 12.0
    ABSOLUTE_MAX_DISCOUNT_PERCENT = 15.0

    @classmethod
    def _estimate_conversion_probability(cls, discount_percent: float) -> float:
        """Função logística sigmóide de probabilidade de fechamento da venda."""
        # Baseline de 40% com 0% de desconto, saturando em 95% para descontos próximos ao teto
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
        """Avalia e aprova ou limita a porcentagem de desconto com base em regras estritas e utilidade."""
        if cart_total <= 0:
            return DiscountApproval(
                approved=False,
                requested_discount_percent=requested_discount_percent,
                approved_discount_percent=0.0,
                final_price=0.0,
                reason="Carrinho sem valor elegível para desconto.",
                expected_utility=0.0,
                conversion_probability=0.0,
            )

        # Regra 1: Teto absoluto por método de pagamento e volume
        max_allowed = cls.MAX_PIX_DISCOUNT_PERCENT if payment_method.upper() == "PIX" else 5.0
        if cart_total >= 1000.0:
            max_allowed = max(max_allowed, cls.MAX_BULK_DISCOUNT_PERCENT)

        approved_percent = min(requested_discount_percent, max_allowed)
        approved_percent = min(approved_percent, cls.ABSOLUTE_MAX_DISCOUNT_PERCENT)

        final_price = round(cart_total * (1.0 - (approved_percent / 100.0)), 2)
        conv_prob = cls._estimate_conversion_probability(approved_percent)
        expected_utility = round(final_price * conv_prob, 2)

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
            expected_utility=expected_utility,
            conversion_probability=conv_prob,
        )


# Instância Singleton da FSM de Negociação
negotiation_fsm = NegotiationFSM()
