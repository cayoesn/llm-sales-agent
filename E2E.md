# Guia de Teste E2E

Este documento descreve como executar o projeto de ponta a ponta usando Docker e verificar o comportamento completo da API e das ferramentas de observabilidade.

## Pré-requisitos
- Docker e Docker Compose instalados.
- `make` instalado (opcional, mas recomendado).

## Iniciar a stack completa

1. Copie o arquivo de exemplo de ambiente: `cp .env.example .env`
2. Inicie a stack: `docker compose up --build`

### O que acontece na inicialização (Lifespan)
Ao subir o container da `api`, o sistema executa um gerenciador de `lifespan` (`app/main.py`). Se `LLM_PROVIDER` for configurado como `ollama`, a API entrará em um loop de espera até que o serviço `ollama-pull-model` termine de baixar o modelo necessário (`llama3.1`), garantindo que a API não responda requisições antes de ter capacidade de processamento.

Os serviços iniciados incluem API, Ollama, Redis, Langfuse (opcional), e a stack de observabilidade (Prometheus, Loki, Promtail, Grafana).

## Teste de fluxo de chat

Abaixo, exemplos de interações principais via `curl`. Use o mesmo `session_id` para manter o contexto na mesma sessão.

### 1. Adicionar e gerenciar carrinho

```bash
# Adicionar
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"sess-1","message":"Quero 2 tênis por 100 reais cada"}'

# Consultar
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"sess-1","message":"Mostrar meu carrinho"}'

# Remover
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"sess-1","message":"Remova os tênis"}'
```

### 2. Checkout e Status

```bash
# Checkout
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"sess-1","message":"Finalizar compra"}'

# Consultar Status (use o ID retornado no checkout)
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"sess-1","message":"Status do pedido <ORDER_ID>"}'
```

## Monitoramento

1. Acesse o Grafana em `http://localhost:3001` (login: `admin` / `admin`).
2. Explore dashboards do Loki (logs da API) e Prometheus (métricas de requisições).

## Validação de qualidade

Para validar o sistema localmente conforme as regras definidas no projeto:

```bash
# Executa testes unitários/integração com coverage > 90%
make coverage

# Executa checks de lint, mypy e segurança
make lint
```

Para encerrar: `docker compose down -v`.
