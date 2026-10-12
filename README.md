# 🤖 LLM Sales Agent (Enterprise Edition)

Agente Autônomo Conversacional de Vendas B2B/B2C com **Graph-RAG & Personalized PageRank (PPR)**, **Utility-Maximizing Negotiation FSM**, Memória de Longo Prazo e Validação Estruturada.

---

## 🌟 Arquitetura & Recursos Big-Tech

- **Graph-RAG com Personalized PageRank (PPR)**:
  - Modelagem do catálogo como Grafo Direcionado de Conhecimento (NetworkX) mapeando compatibilidade, combos e acessórios.
  - Algoritmo Random Walk with Restart (RWR / PPR) centrado nos itens do carrinho:
    $$\mathbf{r} = (1 - \alpha) \mathbf{M}^T \mathbf{r} + \alpha \mathbf{p}$$
    ranqueando recomendações de cross-sell e periféricos por centralidade topológica e relevância relacional.
- **Utility-Maximizing Negotiation FSM**:
  - Máquina de Estados Finitos estrita que previne alucinações de descontos e concessões abusivas pelo modelo.
  - Maximização da utilidade esperada do lojista:
    $$U(d) = \text{Receita Líquida}(d) \cdot P(\text{conversão} \mid d)$$
    onde $P(\text{conversão} \mid d) = \frac{1}{1 + e^{-k(d - d_0)}}$ modela a probabilidade empírica de fechamento.
- **Memória de Longo Prazo Contextual**:
  - Extração contínua de preferências do usuário (orçamento máximo, marcas preferidas, método de pagamento preferencial).
- **Provedores Multi-LLM**:
  - Roteamento dinâmico entre Ollama (Llama-3), Groq e Google Gemini com fallback automático.

---

## 📊 Análise de Algoritmos & Complexidade

| Componente | Algoritmo / Modelo | Complexidade | Propósito |
| :--- | :--- | :--- | :--- |
| **Recuperação de Catálogo** | Híbrido (BM25 + Vetorial + RRF) | $\mathcal{O}(N \log K)$ | Busca textual e semântica resiliente |
| **Cross-Sell / Bundling** | Personalized PageRank (PPR) | $\mathcal{O}(\|V\| + \|E\|)$ | Ranqueamento por centralidade no ecossistema |
| **Guarda de Negociação** | FSM Determinística + Sigmóide de Utilidade | $\mathcal{O}(1)$ | Governança de margem e prevenção de alucinação |

---

## 🚀 Como Executar no Docker

```bash
docker compose up -d --build
```

---

## 🧪 Testes Automatizados (56 Testes / 100% Hermético / 92% Cobertura)

Execução hermética da suíte de testes unitários:

```bash
docker run --rm -v $(pwd):/workspace -w /workspace -e PYTHONPATH=/workspace portfolio-spec-engine:test pytest tests/unit -v --cov=app --cov-report=term-missing
```
