# Desafio Técnico: API Conversacional de Vendas

API FastAPI para um agente de vendas simples, com foco em execução via Docker, testes isolados e cobertura de código controlada.

## Estrutura

- `app/`: aplicação principal, serviços, modelos e middleware.
- `tests/unit/`: testes unitários.
- `tests/integration/`: testes de integração.
- `tests/coverage/`: saída gerada de coverage.

## Requisitos

- Docker e Docker Compose.
- `make` opcional.

## Configuração

1. Copie o ambiente de exemplo:
   ```bash
   cp .env.example .env
   ```
2. Ajuste apenas o que for necessário no `.env`.

## Comandos

- `make run`: sobe a API com Docker.
- `make test`: executa toda a suíte no container de testes.
- `make coverage`: executa a suíte e gera os relatórios em `tests/coverage/`.
- `make lint`: roda `ruff`, `mypy`, `black` e `bandit` dentro do Docker.
- `make docker-up`: sobe a API em background.
- `make docker-down`: derruba os containers.
- `make docker-test`: alias para os testes em Docker.

## Cobertura

- O `pytest` está configurado para falhar abaixo de 90%.
- O arquivo de cobertura fica em `tests/.coverage`.
- O HTML sai em `tests/coverage/html/`.
- O XML sai em `tests/coverage/coverage.xml`.

## Endpoints

- `GET /health`
- `POST /api/v1/chat`
