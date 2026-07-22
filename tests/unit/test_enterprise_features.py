import pytest
from app.llm_logic.graph_rag import GraphRAGEngine, graph_rag_engine
from app.llm_logic.long_term_memory import LongTermMemoryEngine, memory_engine
from app.llm_logic.negotiation_fsm import NegotiationFSM, negotiation_fsm
from app.llm_logic.structured_output import SalesAgentOutputValidator, ConversationalSalesResponse
from app.services import SalesService


@pytest.mark.asyncio
async def test_graph_rag_search():
    engine = GraphRAGEngine()
    results = engine.search_hybrid("iphone e capa", top_k=2)
    assert len(results) > 0
    assert any("iPhone" in r["name"] or "Capa" in r["name"] for r in results)

    # Test graph relations
    iphone_res = [r for r in results if r["id"] == "iphone_15_pro"]
    if iphone_res:
        assert len(iphone_res[0]["graph_relations"]) > 0


@pytest.mark.asyncio
async def test_long_term_memory():
    engine = LongTermMemoryEngine()
    session_id = "test_sess_mem"
    
    profile = engine.extract_and_update_memory(session_id, "Quero um celular Apple com orçamento até R$ 8000 pagando no PIX")
    assert "apple" in profile.preferred_brands
    assert profile.max_budget == 8000.0
    assert profile.payment_preference == "PIX"
    
    prompt_context = engine.format_memory_prompt_context(session_id)
    assert "Preferência declarada pela marca 'Apple'" in prompt_context
    assert "Teto de orçamento de R$ 8000.00" in prompt_context


@pytest.mark.asyncio
async def test_negotiation_fsm():
    fsm = NegotiationFSM()
    
    # Cart total = 500, request = 20% (Should be capped at MAX_PIX_DISCOUNT 10%)
    approval = fsm.evaluate_discount_request(cart_total=500.0, requested_discount_percent=20.0, payment_method="PIX")
    assert approval.approved is True
    assert approval.approved_discount_percent == 10.0
    assert approval.final_price == 450.0

    # Cart total = 1500, request = 10% (Allowed fully)
    approval_bulk = fsm.evaluate_discount_request(cart_total=1500.0, requested_discount_percent=10.0, payment_method="PIX")
    assert approval_bulk.approved is True
    assert approval_bulk.approved_discount_percent == 10.0
    assert approval_bulk.final_price == 1350.0

    # Empty cart
    approval_empty = fsm.evaluate_discount_request(cart_total=0.0, requested_discount_percent=10.0)
    assert approval_empty.approved is False


def test_structured_output_validator():
    fallback = SalesAgentOutputValidator.validate_or_fallback("Olá! Como posso ajudar?")
    assert isinstance(fallback, ConversationalSalesResponse)
    assert fallback.message == "Olá! Como posso ajudar?"

    dict_resp = {
        "message": "Encontrei seu produto!",
        "intent_detected": "search_catalog",
        "recommended_products": [
            {
                "product_name": "iPhone 15 Pro",
                "price": 7299.0,
                "reason_for_recommendation": "Grafo de Conhecimento",
                "discount_applicable": True,
            }
        ],
        "negotiation_applied": False,
        "next_recommended_action": "Adicionar ao carrinho",
    }
    validated = SalesAgentOutputValidator.validate_or_fallback(dict_resp)
    assert validated.intent_detected == "search_catalog"
    assert len(validated.recommended_products) == 1


@pytest.mark.asyncio
async def test_enterprise_service_methods():
    session_id = "test_sess_services"
    
    # 1. Search Catalog Graph RAG
    res_search = await SalesService.search_catalog_graph_rag("apple iphone")
    assert "iPhone 15 Pro" in res_search

    # 2. Add item & Apply Negotiated Discount
    await SalesService.add_to_cart(session_id, "iPhone 15 Pro", 1, 7299.0)
    res_discount = await SalesService.apply_negotiated_discount(session_id, 10.0, "PIX")
    assert "Desconto de 10.0% aprovado" in res_discount or "Valor Total Original" in res_discount

    # 3. Personalized Recommendations
    res_rec = await SalesService.get_personalized_recommendations(session_id)
    assert "Recomendações" in res_rec or "Capa de Silicone MagSafe" in res_rec
