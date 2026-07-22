# 🤖 LLM Sales Agent (Enterprise Edition)

Agente de Vendas Inteligente de Nível Industrial construído com **LangGraph**, **Graph-RAG**, **Mem0** e **FSM de Negociação**.

## 🌟 Arquitetura & Recursos Big-Tech
- **Graph-RAG Engine**: Grafo de conhecimento para mapeamento semântico de produtos, personas de compradores e requisitos.
- **Mem0 Long-Term Memory**: Memória contextual persistente para retenção de preferências e histórico de conversas passadas.
- **Negotiation Finite State Machine (FSM)**: Máquina de estados finitos garantindo transições controladas no fluxo de vendas (Qualificação -> Apresentação -> Objeções -> Fechamento).
- **Structured Outputs**: Saídas estritamente tipadas e validadas via Pydantic.

## 🚀 Como Executar no Docker
```bash
docker compose up -d --build
```

## 🧪 Testes Unitários e Integração (>97% Cobertura)
```bash
docker run --rm -v $(pwd):/app -w /app python:3.12-slim bash -c "pip install pytest pytest-asyncio pytest-cov pydantic pydantic-settings httpx fastapi uvicorn && PYTHONPATH=. pytest"
```
