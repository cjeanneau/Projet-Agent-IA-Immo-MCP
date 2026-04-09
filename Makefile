.PHONY: agent
SHELL := /bin/bash

help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ============================================
# Commande pour lancer l'agent
# ============================================

agent:
	python -m scripts.agent

fastmcp:
	python -m scripts.run_mcp

fastapi:
	python -m scripts.run_api

bpedb:
	python -m scripts.data_bpe_insert

build:
	docker build -f docker/Dockerfile -t fastapi-app:latest .

build-mcp:
	docker build -f docker/Dockerfile.mcp -t mcp-server:latest .

run:
	docker rm -f immo-api || true
	docker run --env-file .env -d -p 8000:8000 --dns 8.8.8.8 --name immo-fastapi-app fastapi-app:latest

run-mcp:
	docker rm -f immo-mcp || true
	docker run --env-file .env -d -p 8100:8100 --dns 8.8.8.8 --name immo-mcp-server mcp-server:latest

stop:
	docker stop immo-api

test:
	coverage run -m pytest

coverage-report:
	coverage report -m

k3s:
	docker save mcp-server:latest | sudo k3s ctr images import -
	docker save fastapi-app:latest | sudo k3s ctr images import -

deploy:
	sudo k3s kubectl apply -f k8s/

k3s-secrets:
	sudo k3s kubectl create secret generic api-keys \
		--from-env-file=.env \
		--dry-run=client -o yaml > /tmp/k3s-secret.yaml
	sudo k3s kubectl apply -f /tmp/k3s-secret.yaml
	rm -f /tmp/k3s-secret.yaml