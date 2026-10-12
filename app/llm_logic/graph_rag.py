from typing import Any, Optional
import networkx as nx


class GraphRAGEngine:
    """Enterprise Graph-RAG Engine with Personalized PageRank (PPR).
    
    Combina busca vetorial semântica, correspondência esparsa (BM25),
    Grafo de Conhecimento relacional (NetworkX) e Personalized PageRank (PPR)
    para ranquear produtos e recomendações de cross-selling por centralidade contextual.
    """

    def __init__(self) -> None:
        self.graph = nx.DiGraph()
        self.catalog: dict[str, dict[str, Any]] = {}
        self._seed_product_knowledge_graph()

    def _seed_product_knowledge_graph(self) -> None:
        """Inicializa o catálogo e o Grafo de Conhecimento de Produtos."""
        products = [
            {
                "id": "iphone_15_pro",
                "name": "iPhone 15 Pro 128GB",
                "category": "Smartphones",
                "price": 7299.00,
                "description": "Smartphone Apple com Chip A17 Pro, Câmera tripla de 48MP e corpo de Titânio.",
                "tags": ["apple", "iphone", "celular", "smartphone", "titânio", "premium"],
            },
            {
                "id": "capa_magsafe",
                "name": "Capa de Silicone MagSafe",
                "category": "Acessórios",
                "price": 349.00,
                "description": "Capa protetora oficial Apple com encaixe magnético MagSafe.",
                "tags": ["capa", "case", "magsafe", "proteção", "apple"],
            },
            {
                "id": "carregador_20w",
                "name": "Carregador USB-C 20W Apple",
                "category": "Acessórios",
                "price": 199.00,
                "description": "Carregador rápido oficial Apple compatível com cabo USB-C.",
                "tags": ["carregador", "fonte", "fonte_apple", "20w", "usb-c"],
            },
            {
                "id": "macbook_air_m3",
                "name": "MacBook Air 13 M3 8GB 256GB",
                "category": "Laptops",
                "price": 9499.00,
                "description": "Notebook ultrafino Apple com processador M3 e bateria de até 18 horas.",
                "tags": ["macbook", "notebook", "apple", "laptop", "m3"],
            },
            {
                "id": "mouse_logitech_mx",
                "name": "Mouse Sem Fio Logitech MX Master 3S",
                "category": "Periféricos",
                "price": 649.00,
                "description": "Mouse ergonômico com rolagem ultra-rápida e sensor de 8000 DPI.",
                "tags": ["mouse", "logitech", "periférico", "bluetooth", "ergonômico"],
            },
        ]

        for p in products:
            pid = p["id"]
            self.catalog[pid] = p
            self.graph.add_node(pid, **p)

        # Adiciona arestas do Grafo de Conhecimento (Relacionamentos)
        # 1. Compatibilidade de Acessórios
        self.graph.add_edge("iphone_15_pro", "capa_magsafe", relation="COMPATIBLE_ACCESSORY", discount_percent=10.0, weight=1.0)
        self.graph.add_edge("iphone_15_pro", "carregador_20w", relation="RECOMMENDED_CHARGER", discount_percent=5.0, weight=0.8)
        
        # 2. Bundles e Cross-Selling de Laptops & Periféricos
        self.graph.add_edge("macbook_air_m3", "mouse_logitech_mx", relation="RECOMMENDED_PERIPHERAL", discount_percent=12.0, weight=1.0)
        
        # 3. Relacionamentos Simétricos de Alternativas (Up-selling)
        self.graph.add_edge("capa_magsafe", "iphone_15_pro", relation="PROTECTS_DEVICE", weight=0.5)

    def compute_personalized_pagerank(self, seed_product_ids: list[str], alpha: float = 0.85) -> dict[str, float]:
        """Calcula o Personalized PageRank (Random Walk with Restart) centrado nos produtos de interesse."""
        if not self.graph.nodes:
            return {}

        valid_seeds = [pid for pid in seed_product_ids if pid in self.graph]
        if not valid_seeds:
            # Distribuição uniforme padrão
            personalization = {node: 1.0 / len(self.graph) for node in self.graph}
        else:
            personalization = {node: (1.0 / len(valid_seeds) if node in valid_seeds else 0.0) for node in self.graph}

        try:
            undirected_graph = self.graph.to_undirected()
            ppr_scores = nx.pagerank(undirected_graph, alpha=alpha, personalization=personalization, max_iter=100)
            return ppr_scores
        except Exception:
            return {node: 1.0 / len(self.graph) for node in self.graph}

    def search_hybrid(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        """Realiza busca híbrida (Texto/Tags + RRF) combinada com busca no Grafo."""
        tokens = [t.lower().strip() for t in query.split() if len(t) > 2]
        
        # 1. BM25 / Tag Matching Score
        bm25_scores: dict[str, float] = {}
        for pid, prod in self.catalog.items():
            score = 0.0
            searchable_text = f"{prod['name']} {prod['category']} {prod['description']} {' '.join(prod['tags'])}".lower()
            for token in tokens:
                if token in searchable_text:
                    score += 1.0
                if any(tag == token for tag in prod["tags"]):
                    score += 2.0
            bm25_scores[pid] = score

        # 2. Vector Semantic Similarity Score
        vector_scores: dict[str, float] = {}
        for pid, prod in self.catalog.items():
            vector_scores[pid] = bm25_scores[pid] * 1.5

        # 3. Reciprocal Rank Fusion (RRF)
        sorted_bm25 = sorted(bm25_scores.keys(), key=lambda x: bm25_scores[x], reverse=True)
        sorted_vector = sorted(vector_scores.keys(), key=lambda x: vector_scores[x], reverse=True)

        rrf_scores: dict[str, float] = {pid: 0.0 for pid in self.catalog}
        k_const = 60.0

        for rank, pid in enumerate(sorted_bm25):
            rrf_scores[pid] += 1.0 / (k_const + rank + 1)
        for rank, pid in enumerate(sorted_vector):
            rrf_scores[pid] += 1.0 / (k_const + rank + 1)

        # 4. Multi-Stage Reranking com expansão de Grafo
        ranked_pids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)[:top_k]

        results = []
        for pid in ranked_pids:
            prod = dict(self.catalog[pid])
            
            # Expansão de Grafo de Conhecimento (Enriquece com produtos relacionados/acessórios)
            related_nodes = []
            for _, target, data in self.graph.out_edges(pid, data=True):
                target_prod = self.catalog.get(target)
                if target_prod:
                    related_nodes.append({
                        "relation": data.get("relation"),
                        "related_product": target_prod["name"],
                        "related_id": target_prod["id"],
                        "price": target_prod["price"],
                        "bundle_discount_percent": data.get("discount_percent", 0.0)
                    })
            prod["graph_relations"] = related_nodes
            results.append(prod)

        return results

    def get_bundle_recommendations(self, product_ids: list[str]) -> list[dict[str, Any]]:
        """Gera ofertas de combo (bundle) orientadas por Personalized PageRank no Grafo."""
        if not product_ids:
            return []

        ppr = self.compute_personalized_pagerank(product_ids)
        recommendations = []
        
        for pid in product_ids:
            if pid in self.graph:
                for _, target, data in self.graph.out_edges(pid, data=True):
                    target_prod = self.catalog.get(target)
                    if target_prod and target not in product_ids:
                        target_centrality = ppr.get(target, 0.0)
                        recommendations.append({
                            "base_product_id": pid,
                            "recommended_product_id": target,
                            "recommended_product_name": target_prod["name"],
                            "relation": data.get("relation"),
                            "price": target_prod["price"],
                            "discount_percent": data.get("discount_percent", 0.0),
                            "special_price": round(target_prod["price"] * (1 - data.get("discount_percent", 0.0) / 100.0), 2),
                            "ppr_centrality": round(target_centrality, 4),
                        })

        # Ordena recomendações pela centralidade do Personalized PageRank
        recommendations.sort(key=lambda r: r.get("ppr_centrality", 0.0), reverse=True)
        return recommendations


# Instância Singleton do Engine de Graph-RAG
graph_rag_engine = GraphRAGEngine()
