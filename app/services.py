import secrets
import json
import uuid
from typing import Any

from app.models import Cart, CartItem, ConversationSession, Order, OrderStatus
from app.repository import repo
from app.llm_logic.graph_rag import graph_rag_engine
from app.llm_logic.long_term_memory import memory_engine
from app.llm_logic.negotiation_fsm import negotiation_fsm


class SalesService:
    @staticmethod
    async def get_or_create_cart(session_id: str) -> Cart:
        """Recupera o carrinho existente ou cria um novo para a sessão do usuário."""
        if session_id not in repo.carts:
            repo.carts[session_id] = Cart(session_id=session_id)
        return repo.carts[session_id]

    @staticmethod
    async def add_to_cart(
        session_id: str, product_name: str, quantity: int, price: float = 0.0
    ) -> str:
        """Adiciona um produto ao carrinho com nome, quantidade e preço."""
        cart = await SalesService.get_or_create_cart(session_id)
        product_id = product_name.lower().replace(" ", "_")

        # Update or add item
        for item in cart.items:
            if item.product_id == product_id:
                item.quantity += quantity
                repo.carts[session_id] = cart
                return f"Atualizado {product_name} para {item.quantity} unidades."

        cart.items.append(
            CartItem(
                product_id=product_id, name=product_name, quantity=quantity, price=price
            )
        )
        repo.carts[session_id] = cart
        return f"Adicionado {quantity}x {product_name} ao carrinho."

    @staticmethod
    async def remove_from_cart(session_id: str, product_name: str) -> str:
        """Remove um produto específico do carrinho."""
        cart = await SalesService.get_or_create_cart(session_id)
        product_id = product_name.lower().replace(" ", "_")
        cart.items = [item for item in cart.items if item.product_id != product_id]
        repo.carts[session_id] = cart
        return f"Removido {product_name} do carrinho."

    @staticmethod
    async def clear_cart(session_id: str) -> str:
        """Limpa todos os itens do carrinho do usuário."""
        if session_id in repo.carts:
            del repo.carts[session_id]
        return "Carrinho vazio."

    @staticmethod
    async def show_cart(session_id: str) -> str:
        """Mostra os itens atuais do carrinho e o total acumulado."""
        cart = await SalesService.get_or_create_cart(session_id)
        if not cart.items:
            return "Seu carrinho está vazio."

        lines = []
        total = 0.0
        for item in cart.items:
            item_total = item.price * item.quantity
            total += item_total
            lines.append(
                f"{item.quantity}x {item.name} - R$ {item.price:.2f} cada - Total R$ {item_total:.2f}"
            )

        lines.append(f"Total do carrinho: R$ {total:.2f}")
        return "\n".join(lines)

    @staticmethod
    async def checkout(session_id: str) -> str:
        """Finaliza o pedido e gera um código PIX para pagamento."""
        cart = await SalesService.get_or_create_cart(session_id)
        if not cart.items:
            return "Carrinho está vazio."

        total = sum(item.price * item.quantity for item in cart.items)
        order_id = str(uuid.uuid4())
        pix = f"PIX_CODE_{order_id}_{total:.2f}"

        order = Order(
            id=order_id,
            session_id=session_id,
            items=cart.items,
            total_price=total,
            pix_copy_paste=pix,
        )
        repo.orders[order_id] = order
        await SalesService.clear_cart(session_id)

        return f"Pedido {order_id} realizado com sucesso! Total: R$ {total:.2f}\nPIX: {pix}"

    @staticmethod
    async def get_order_status(order_id: str) -> str:
        """Consulta o status de um pedido usando o ID do pedido."""
        order = repo.orders.get(order_id)
        if not order:
            return OrderStatus.NOT_FOUND.value
        return secrets.choice([OrderStatus.PROCESSING.value, OrderStatus.SHIPPED.value])

    @staticmethod
    async def get_session(session_id: str) -> ConversationSession:
        """Recupera ou cria uma sessão de conversa para o usuário."""
        if session_id not in repo.sessions:
            repo.sessions[session_id] = ConversationSession(session_id=session_id)
        return repo.sessions[session_id]

    @staticmethod
    async def search_catalog_graph_rag(query: str) -> str:
        """Busca produtos usando Graph-RAG Híbrido com expansão de Grafo e RRF."""
        results = graph_rag_engine.search_hybrid(query, top_k=3)
        if not results:
            return "Nenhum produto encontrado no catálogo para a busca."

        formatted_lines = []
        for prod in results:
            line = f"📦 {prod['name']} - R$ {prod['price']:.2f}\n  Descrição: {prod['description']}"
            if prod.get("graph_relations"):
                relations = ", ".join([
                    f"{r['related_product']} ({r['relation']})"
                    for r in prod["graph_relations"]
                ])
                line += f"\n  💡 Itens Relacionados/Acessórios: {relations}"
            formatted_lines.append(line)

        return "\n\n".join(formatted_lines)

    @staticmethod
    async def apply_negotiated_discount(
        session_id: str, requested_discount_percent: float, payment_method: str = "PIX"
    ) -> str:
        """Aplica desconto negociado no carrinho com validação estrita da FSM."""
        cart = await SalesService.get_or_create_cart(session_id)
        if not cart.items:
            return "Carrinho vazio. Adicione produtos antes de negociar descontos."

        cart_total = sum(item.price * item.quantity for item in cart.items)
        approval = negotiation_fsm.evaluate_discount_request(
            cart_total=cart_total,
            requested_discount_percent=requested_discount_percent,
            payment_method=payment_method,
        )

        return f"{approval.reason}\nValor Total Original: R$ {cart_total:.2f} -> Valor com Desconto: R$ {approval.final_price:.2f}"

    @staticmethod
    async def get_personalized_recommendations(session_id: str) -> str:
        """Gera recomendações personalizadas com base na Memória de Longo Prazo e Grafo."""
        profile = memory_engine.get_or_create_profile(session_id)
        cart = await SalesService.get_or_create_cart(session_id)

        cart_product_ids = [item.product_id for item in cart.items]
        recommendations = graph_rag_engine.get_bundle_recommendations(cart_product_ids)

        if not recommendations:
            return "Adicione produtos ao seu carrinho para visualizar ofertas de combos e acessórios recomendados!"

        lines = ["🎯 Recomendações Personalizadas e Combos de Desconto:"]
        for rec in recommendations:
            lines.append(
                f"- Para seu item do carrinho, recomendamos: {rec['recommended_product_name']} por R$ {rec['special_price']:.2f} (Desconto de {rec['discount_percent']}%)"
            )

        return "\n".join(lines)
