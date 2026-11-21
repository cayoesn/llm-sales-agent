# 🤖 LLM Sales Agent (Enterprise Edition)

Autonomous B2B/B2C Conversational Sales Agent with **Graph-RAG & Personalized PageRank (PPR)**, **Utility-Maximizing Negotiation FSM**, Long-Term Memory, and Structured Output Validation.

---

## 🌟 Architecture & Enterprise Features

- **Graph-RAG with Personalized PageRank (PPR)**:
  - Models the product catalog as a Directed Knowledge Graph (NetworkX) mapping compatibility, bundles, and accessories.
  - Runs Random Walk with Restart (RWR / PPR) centered on items in the shopping cart:
    $$\mathbf{r} = (1 - \alpha) \mathbf{M}^T \mathbf{r} + \alpha \mathbf{p}$$
    ranking cross-sell and peripheral recommendations by topological centrality and relational relevance.
- **Utility-Maximizing Negotiation FSM**:
  - Strict Finite State Machine that prevents discount hallucinations and unauthorized concessions by the LLM.
  - Maximizes the merchant's expected utility:
    $$U(d) = \text{Net Revenue}(d) \cdot P(\text{conversion} \mid d)$$
    where $P(\text{conversion} \mid d) = \frac{1}{1 + e^{-k(d - d_0)}}$ models the empirical closing probability.
- **Contextual Long-Term Memory**:
  - Continuously extracts user preferences (maximum budget, preferred brands, preferred payment method).
- **Multi-LLM Providers**:
  - Dynamic routing across Ollama (Llama-3), Groq, and Google Gemini with automatic fallback.

---

## 📊 Algorithms & Complexity Analysis

| Component | Algorithm / Model | Complexity | Purpose |
| :--- | :--- | :--- | :--- |
| **Catalog Retrieval** | Hybrid (BM25 + Vector + RRF) | $\mathcal{O}(N \log K)$ | Resilient lexical and semantic search |
| **Cross-Sell / Bundling** | Personalized PageRank (PPR) | $\mathcal{O}(\|V\| + \|E\|)$ | Ecosystem centrality ranking |
| **Negotiation Guard** | Deterministic FSM + Utility Sigmoid | $\mathcal{O}(1)$ | Margin governance and hallucination prevention |

---

## 🚀 Running with Docker

```bash
docker compose up -d --build
```

---

## 🧪 Automated Tests (56 Tests / 100% Hermetic / 92% Coverage)

Hermetic execution of the unit test suite:

```bash
docker run --rm -v $(pwd):/workspace -w /workspace -e PYTHONPATH=/workspace portfolio-spec-engine:test pytest tests/unit -v --cov=app --cov-report=term-missing
```
