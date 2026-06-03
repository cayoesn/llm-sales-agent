.PHONY: install run test lint coverage docker-up docker-down docker-test

install:
	docker compose -f docker-compose.yml -f docker-compose.test.yml build api tests

run:
	docker compose up --build api

test:
	docker compose -f docker-compose.test.yml run --rm tests

lint:
	docker compose -f docker-compose.test.yml run --rm tests sh -lc "ruff check app tests && mypy app && black --check app tests && bandit -r app"

coverage:
	docker compose -f docker-compose.test.yml run --rm tests

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

docker-test:
	docker compose -f docker-compose.test.yml run --rm tests
