.PHONY: agent help
SHELL := /bin/bash

help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ============================================
# Dev
# ============================================

agent: ## Lance l'agent en local
	python -m scripts.agent

fastmcp: ## Lance le serveur MCP en local
	python -m scripts.run_mcp

fastapi: ## Lance l'API FastAPI en local
	python -m scripts.run_api

bpedb: ## Insère les données BPE
	python -m scripts.data_bpe_insert

test: ## Lance les tests
	coverage run -m pytest

coverage-report: ## Affiche le rapport de couverture
	coverage report -m

# ============================================
# Docker
# ============================================

build: ## Build les deux images Docker
	docker build -f docker/Dockerfile.api -t fastapi-app:latest .
	docker build -f docker/Dockerfile.mcp -t mcp-server:latest .

build-api: ## Build l'image FastAPI
	docker build -f docker/Dockerfile.api -t fastapi-app:latest .

build-mcp: ## Build l'image MCP
	docker build -f docker/Dockerfile.mcp -t mcp-server:latest .

run: ## Lance le conteneur FastAPI
	docker rm -f immo-fastapi-app || true
	docker run --env-file .env -d -p 8000:8000 --dns 8.8.8.8 --name immo-fastapi-app fastapi-app:latest

run-mcp: ## Lance le conteneur MCP
	docker rm -f immo-mcp-server || true
	docker run --env-file .env -d -p 8100:8100 --dns 8.8.8.8 --name immo-mcp-server mcp-server:latest

stop: ## Stoppe les conteneurs
	docker stop immo-fastapi-app immo-mcp-server || true

# ============================================
# K3S local
# ============================================

k3s-import: ## Importe les images dans K3S
	docker save mcp-server:latest | sudo k3s ctr images import -
	docker save fastapi-app:latest | sudo k3s ctr images import -

k3s-secrets: ## Injecte les secrets depuis .env
	sudo k3s kubectl create secret generic api-keys \
		--from-env-file=.env \
		--dry-run=client -o yaml > /tmp/k3s-secret.yaml
	sudo k3s kubectl apply -f /tmp/k3s-secret.yaml
	rm -f /tmp/k3s-secret.yaml

deploy: ## Déploie sur K3S local
	sed -e "s|__PROJECT_ROOT__|$(CURDIR)|g" \
	    -e "s|__MCP_IMAGE__|mcp-server:latest|g" \
	    -e "s|__PULL_POLICY__|Never|g" \
	    -e "s|__NAMESPACE__|default|g" \
	    -e "s|__NODE_PORT__|30080|g" \
	    -e "/__IMAGE_PULL_SECRETS__/d" \
	    k8s/mcp-server.yaml | sudo k3s kubectl apply -f -
	sed -e "s|__API_IMAGE__|fastapi-app:latest|g" \
	    -e "s|__PULL_POLICY__|Never|g" \
	    -e "s|__NAMESPACE__|default|g" \
	    -e "s|__NODE_PORT__|30080|g" \
	    -e "/__IMAGE_PULL_SECRETS__/d" \
	    k8s/fastapi-app.yaml | sudo k3s kubectl apply -f -
	sudo k3s kubectl rollout restart deployment mcp-server
	sudo k3s kubectl rollout restart deployment fastapi-app

k3s-install: build k3s-import k3s-secrets deploy ## Build, importe, configure et déploie sur K3S local

k3s-prune: ## Nettoie les images inutilisées
	sudo k3s crictl rmi --prune

k3s-status: ## Affiche l'état des pods
	sudo k3s kubectl get pods

k3s-logs-api: ## Logs FastAPI
	sudo k3s kubectl logs -l app=fastapi-app --tail=50

k3s-logs-mcp: ## Logs MCP server
	sudo k3s kubectl logs -l app=mcp-server --tail=50

# ============================================
# Remote deploy
# ============================================

dump-artifacts: ## Copie les données sur le serveur distant
	./scripts/deploy/artifacts.sh p4g1@datalab.myconnectech.fr
