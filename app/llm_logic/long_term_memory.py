import re

from pydantic import BaseModel, Field


class CustomerProfile(BaseModel):
    """Customer Long-Term Memory Profile (Mem0 Pattern)."""

    session_id: str
    preferred_categories: list[str] = Field(default_factory=list)
    preferred_brands: list[str] = Field(default_factory=list)
    max_budget: float | None = None
    payment_preference: str | None = None
    extracted_facts: list[str] = Field(default_factory=list)


class LongTermMemoryEngine:
    """Enterprise Long-Term Memory Engine.

    Autonomously extracts facts, preferences, favorite brands, and budget
    constraints from customer dialogue and injects a summarized context.
    """

    def __init__(self) -> None:
        self.profiles: dict[str, CustomerProfile] = {}

    def get_or_create_profile(self, session_id: str) -> CustomerProfile:
        if session_id not in self.profiles:
            self.profiles[session_id] = CustomerProfile(session_id=session_id)
        return self.profiles[session_id]

    def extract_and_update_memory(
        self, session_id: str, message: str
    ) -> CustomerProfile:
        """Extract facts from the user message and update persistent memory."""
        profile = self.get_or_create_profile(session_id)
        lower_msg = message.lower()

        # 1. Extract Preferred Brands
        brands = ["apple", "logitech", "samsung", "dell", "sony"]
        for brand in brands:
            if brand in lower_msg and brand not in profile.preferred_brands:
                profile.preferred_brands.append(brand)
                profile.extracted_facts.append(
                    f"Stated preference for brand '{brand.capitalize()}'."
                )

        # 2. Extract Budget (e.g., "up to 8000", "up to $8000", "max 1000")
        budget_match = re.search(
            r"(?:up to|max|maximum|budget|spending|at most)?\s*(?:\$\s*|usd\s*)?(\d+(?:,\d{3})*(?:\.\d+)?)",
            lower_msg,
        )
        if budget_match:
            try:
                raw_num = budget_match.group(1).replace(",", "")
                val = float(raw_num)
                if val > 50:  # Avoid capturing small quantities such as item counts
                    profile.max_budget = val
                    fact_str = f"Budget cap of ${val:.2f}."
                    if fact_str not in profile.extracted_facts:
                        profile.extracted_facts.append(fact_str)
            except ValueError:
                pass

        # 3. Payment Preference (PIX, Credit Card)
        if "pix" in lower_msg:
            profile.payment_preference = "PIX"
            if "Preference for payment via PIX." not in profile.extracted_facts:
                profile.extracted_facts.append("Preference for payment via PIX.")
        elif "credit card" in lower_msg or "card" in lower_msg or "credit" in lower_msg:
            profile.payment_preference = "Credit Card"
            if "Preference for payment via Credit Card." not in profile.extracted_facts:
                profile.extracted_facts.append(
                    "Preference for payment via Credit Card."
                )

        return profile

    def format_memory_prompt_context(self, session_id: str) -> str:
        """Format extracted long-term memory facts for injection into the system prompt."""
        profile = self.get_or_create_profile(session_id)
        if not profile.extracted_facts:
            return ""

        facts_str = "\n".join([f"- {fact}" for fact in profile.extracted_facts])
        return (
            f"\n[CUSTOMER LONG-TERM MEMORY]:\n{facts_str}\n"
            "Subtly use these preferences when recommending products and discounts."
        )


# Singleton instance of the Long-Term Memory Engine
memory_engine = LongTermMemoryEngine()
