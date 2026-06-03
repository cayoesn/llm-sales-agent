# Guia de Teste E2E

Este documento descreve como executar o projeto de ponta a ponta usando Docker e verificar o comportamento completo da API e das ferramentas de observabilidade.

## Preparar o ambiente

1. Copie o arquivo de exemplo de ambiente:

```bash
cp .env.example .env
```

2. Se desejar, edite `.env` para ajustar valores como `LLM_PROVIDER`, `OLLAMA_BASE_URL` ou credenciais de `LANGFUSE`.

## Iniciar a stack completa

Execute:

```bash
docker compose up --build
```

Os serviços que serão iniciados são:
- `api` em `http://localhost:8000`
- `ollama` em `http://localhost:11434`
- `redis` em `localhost:6379`
- `langfuse` em `http://localhost:3000`
- `prometheus` em `http://localhost:9090`
- `loki` em `http://localhost:3100`
- `grafana` em `http://localhost:3001`

**Aguarde 2-5 minutos** para que o container `ollama-pull-model` baixe e configure o modelo `llama3.1`. Você verá uma mensagem como `Model llama3.1 is ready!` nos logs quando estiver pronto.

## Verificar o estado do serviço

1. Cheque se a API está saudável:

```bash
curl http://localhost:8000/health
```

2. O serviço `ollama-pull-model` puxa o modelo `llama7b` automaticamente para a instância de Ollama.

## Teste de fluxo de chat

### 1. Adicionar Produto ao Carrinho

Envie uma mensagem para adicionar um item ao carrinho:

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"user-session-12345","message":"Quero adicionar 2 tênis de corrida ao meu carrinho."}'
```

**Resposta esperada:**
```json
{
  "session_id": "user-session-12345",
  "response": "Perfeito! Já adicionei 2 tênis de corrida ao seu carrinho. Deseja adicionar mais alguma coisa ou quer fechar o pedido?"
}
```

### 2. Adicionar Outro Produto

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"user-session-12345","message":"Quero adicionar um teclado por 250 reais"}'
```

### 3. Remover Produto do Carrinho

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"user-session-12345","message":"Remova o teclado do meu carrinho"}'
```

### 4. Limpar Carrinho

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"user-session-12345","message":"Limpar meu carrinho"}'
```

### 5. Consultar itens do carrinho

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"user-session-12345","message":"Mostrar meu carrinho"}'
```

### 6. Checkout Simulado (PIX)

Comece adicionando um item novamente:

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"user-session-12345","message":"Quero adicionar um mouse por 80 reais"}'
```

Depois finalize a compra:

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"user-session-12345","message":"Quero finalizar a compra e pagar com PIX"}'
```

**Resposta esperada:**
Conterá um ID de pedido único e uma chave PIX "copia e cola" com o valor total.

### 7. Consultar Status de Pedido

Use o ID de pedido retornado no checkout anterior:

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"user-session-12345","message":"Qual é o status do pedido <ORDER_ID>?"}'
```

**Resposta esperada:**
O status será aleatoriamente "Processando" ou "Enviado".

### 7. Consultar Pedido Inexistente

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"user-session-12345","message":"Qual é o status do pedido non-existent-id?"}'
```

**Resposta esperada:**
O agente informará que o pedido não foi encontrado.

### 8. Persistência entre Sessões

Use um novo `session_id` e adicione itens. Os dados do carrinho anterior (com outro `session_id`) não serão acessíveis:

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"new-session","message":"Mostre meu carrinho"}'
```

Isso valida a integração do `api` com o agente, as ferramentas de carrinho e o repositório em memória.

## Monitoramento e logs

1. Acesse o Grafana em `http://localhost:3001`.
2. Faça login com o usuário padrão:
   - usuário: `admin`
   - senha: `admin`
3. Use a fonte de dados `Loki` para ver os logs centralizados.
4. Use a fonte de dados `Prometheus` para consultar métricas.

## Encerrar a stack

Quando terminar, pare os containers e remova volumes temporários:

```bash
docker compose down -v
```

## Validar com testes

Execute a suíte de testes do projeto:

```bash
make test
```

Para gerar cobertura e validar qualidade de código:

```bash
make coverage
make lint
```
