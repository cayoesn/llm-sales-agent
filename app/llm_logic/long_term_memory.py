import re
from typing import Any
from pydantic import BaseModel, Field


class CustomerProfile(BaseModel):
    """Perfil de Memória de Longo Prazo do Cliente (Mem0 Pattern)."""
    session_id: str
    preferred_categories: list[str] = Field(default_factory=list)
    preferred_brands: list[str] = Field(default_factory=list)
    max_budget: float | None = None
    payment_preference: str | None = None
    extracted_facts: list[str] = Field(default_factory=list)


class LongTermMemoryEngine:
    """Enterprise Long-Term Memory Engine.
    
    Extrai autonomamente fatos, preferências, marca favorita e restrições
    de orçamento do diálogo do cliente e injeta um contexto sumarizado.
    """

    def __init__(self) -> None:
        self.profiles: dict[str, CustomerProfile] = {}

    def get_or_create_profile(self, session_id: str) -> CustomerProfile:
        if session_id not in self.profiles:
            self.profiles[session_id] = CustomerProfile(session_id=session_id)
        return self.profiles[session_id]

    def extract_and_update_memory(self, session_id: str, message: str) -> CustomerProfile:
        """Extrai fatos da mensagem do usuário e atualiza a memória persistente."""
        profile = self.get_or_create_profile(session_id)
        lower_msg = message.lower()

        # 1. Extração de Marcas de Preferência
        brands = ["apple", "logitech", "samsung", "dell", "sony"]
        for brand in brands:
            if brand in lower_msg and brand not in profile.preferred_brands:
                profile.preferred_brands.append(brand)
                profile.extracted_facts.append(f"Preferência declarada pela marca '{brand.capitalize()}'.")

        # 2. Extração de Orçamento (ex: "até 5000", "máximo 1000 reais")
        budget_match = re.search(r"(?:até|máximo|orçamento|gastando|no máximo)\s*(?:R\$\s*)?(\d+(?:\.\d+)?|\d+)", lower_msg)
        if budget_match:
            try:
                val = float(budget_match.group(1).replace(".", ""))
                profile.max_budget = val
                profile.extracted_facts.append(f"Teto de orçamento de R$ {val:.2f}.")
            except ValueError:
                pass

        # 3. Preferência de Pagamento (PIX, Cartão, Boleto)
        if "pix" in lower_msg:
            profile.payment_preference = "PIX"
            if "Preferência por pagamento via PIX." not in profile.extracted_facts:
                profile.extracted_facts.append("Preferência por pagamento via PIX.")
        elif "cartão" in lower_msg or "credito" in lower_msg or "crédito" in lower_msg:
            profile.payment_preference = "Cartão de Crédito"
            if "Preferência por pagamento via Cartão de Crédito." not in profile.extracted_facts:
                profile.extracted_facts.append("Preferência por pagamento via Cartão de Crédito.")

        return profile

    def format_memory_prompt_context(self, session_id: str) -> str:
        """Formata os fatos extraídos da memória de longo prazo para injeção no System Prompt."""
        profile = self.get_or_create_profile(session_id)
        if not profile.extracted_facts:
            return ""

        facts_str = "\n".join([f"- {fact}" for fact in profile.extracted_facts])
        return f"\n[MEMÓRIA DE LONGO PRAZO DO CLIENTE]:\n{facts_str}\nUtilize essas preferências sutilmente ao recomendar produtos e descontos."


# Instância Singleton do Long-Term Memory Engine
memory_engine = LongTermMemoryEngine()
