# Projet Immo - Prédiction de Prix Immobiliers

Application de prédiction du prix de biens immobiliers basée sur l'apprentissage automatique et un agent IA conversationnel.

## Description

Ce projet met à disposition une application permettant d'estimer le prix d'un bien immobilier en fonction de ses caractéristiques (localisation, surface, nombre de pièces, etc.). Il repose sur une architecture à deux services : une API FastAPI pour l'interface utilisateur et un serveur MCP (Model Context Protocol) exposant les outils métier (geocoding, transactions, estimation, équipements).

## Fonctionnalités

- Prédiction du prix d'un bien immobilier via un modèle XGBoost/Scikit-learn
- Interface web pour saisir les caractéristiques du bien
- Chatbot intelligent (Mistral AI) avec streaming pour l'assistance utilisateur
- Consultation des transactions immobilières récentes (API DVF+ Cerema)
- Consultation des équipements communaux (BPE INSEE via DuckDB)
- Geocoding d'adresses (geo.api.gouv.fr)
- Monitoring Prometheus + Grafana

## Architecture

Le projet suit une architecture microservices avec deux applications distinctes :

```mermaid
graph LR
    U[Utilisateur] -->|Web / API| FA

    subgraph K3S["K3S Cluster — namespace p4g1"]
        direction LR
        subgraph POD_API["Pod FastAPI"]
            FA[FastAPI :8000]
        end
        subgraph POD_MCP["Pod MCP Server"]
            MCP[MCP :8100]
        end
        FA -->|MCP Protocol| MCP
    end

    FA -.->|API| LLM[Mistral AI]

    MCP --> GEO[geo.api.gouv.fr]
    MCP --> DVF[API DVF+ Cerema]
    MCP --> MODEL[XGBoost]
    MCP --> DB[(DuckDB)]
```

### Applications

| Service | Port | Description |
|---------|------|-------------|
| **FastAPI** | 8000 | API REST, interface web, chatbot, agent LangChain |
| **MCP Server** | 8100 | Outils métier : geocoding, transactions, estimation, équipements |

### Outils MCP

1. **geocoding_tools** : Conversion d'adresse en coordonnées GPS et code INSEE
2. **commune_info_tools** : Équipements de la commune (BPE INSEE)
3. **recent_transactions_tools** : Ventes immobilières récentes (API Cerema, cache disque 30 jours)
4. **estimation_tools** : Prédiction de prix (modèle XGBoost sérialisé)

## Technologies

- **Python 3.12** / **uv** : Gestion des dépendances
- **FastAPI** / **Uvicorn** : API REST et interface web
- **FastMCP** : Serveur MCP pour les outils métier
- **LangChain** / **Mistral AI** : Agent IA conversationnel
- **Scikit-learn** / **XGBoost** : Modèle de prédiction
- **DuckDB** : Base de données équipements INSEE
- **Prometheus** / **Grafana** : Monitoring
- **Docker** : Conteneurisation (multi-stage builds, groupes de dépendances)
- **K3S** : Orchestration Kubernetes
- **Ansible** : Déploiement automatisé
- **GitHub Actions** : CI/CD (tests, build, deploy)
- **DVC** : Versioning des données
- **MLflow** / **Optuna** : Entraînement et optimisation des modèles
- **LangSmith** : Monitoring de l'agent IA

## Installation

### Prérequis

- Python 3.12+
- uv
- make
- Un fichier `.env` (suivre `.env.exemple`)

### Étapes

```bash
# Cloner le dépôt
git clone https://github.com/cjeanneau/Projet-Agent-IA-Immo-MCP.git
cd Projet-Agent-IA-Immo-MCP

# Installer toutes les dépendances
uv sync --all-groups

# Ou installer uniquement pour un service
uv sync --group fastapi   # API uniquement
uv sync --group mcp       # MCP uniquement
```

## Utilisation

### Lancer les services localement

```bash
make fastapi    # Lance l'API FastAPI sur :8000
make fastmcp    # Lance le serveur MCP sur :8100
```

L'interface web est accessible à `http://localhost:8000` et la documentation API à `http://localhost:8000/docs`.

### Entraîner un modèle

```bash
python -m scripts.model_training_mlflow
```

### Lancer les tests

```bash
make test
make coverage-report
```

## Déploiement

### Docker

Les Dockerfiles utilisent des builds multi-stage et des groupes de dépendances uv pour des images optimisées. Le stage `builder` installe les dépendances avec uv, puis le stage final copie uniquement le venv et le code applicatif (sans uv ni outils de build).

```bash
# Construire les images
make build       # Image FastAPI (~330 MB)
make build-mcp   # Image MCP (~1.25 GB)

# Lancer les conteneurs
make run         # Lance FastAPI
make run-mcp     # Lance MCP
```

### K3S local

Pour déployer localement sur un cluster K3S :

```bash
make k3s-install
```

### Déploiement en production (CI/CD)

Le déploiement en production est entièrement automatisé via GitHub Actions et se décompose en trois workflows :

#### 1. Tests (`tests.yml`)

Exécuté sur chaque push sur `main` et `staging`.

```mermaid
flowchart LR
    Push["Push main / staging"] --> Checkout
    Checkout --> Python["Setup Python 3.12"]
    Python --> UV["Install uv"]
    UV --> Deps["uv sync --all-extras"]
    Deps --> Tests["pytest"]
```

#### 2. Build (`build.yml`)

Exécuté sur chaque push sur `main`. Construit les images Docker et les pousse sur GitHub Container Registry (GHCR).

```mermaid
flowchart TD
    Push["Push sur main"] --> Checkout["Checkout du code"]
    Checkout --> Login["Login GHCR"]
    Login --> BuildMCP["Build Dockerfile.mcp"]
    Login --> BuildAPI["Build Dockerfile.api"]
    BuildMCP --> PushMCP["Push ghcr.io/.../mcp-server:latest\nghcr.io/.../mcp-server:sha"]
    BuildAPI --> PushAPI["Push ghcr.io/.../fastapi-app:latest\nghcr.io/.../fastapi-app:sha"]
```

#### 3. Deploy (`deploy.yml`)

Déclenché automatiquement après un build réussi ou manuellement via `workflow_dispatch`. Se connecte au serveur de production en SSH et exécute un playbook Ansible.

```mermaid
flowchart LR
    Trigger["Build réussi\nou workflow_dispatch"] --> SSH["Connexion SSH\nau serveur"]
    SSH --> Playbook["Ansible Playbook"]
    Playbook --> Secrets["Secrets K8S\n(GHCR + API keys)"]
    Secrets --> Apply["kubectl apply\n(manifests K8S)"]
    Apply --> Restart["Rollout restart"]
```

Le playbook Ansible (`ansible_playbook.yml`) gère l'intégralité de la configuration K3S sur le serveur distant :
- Création du namespace `p4g1`
- Gestion des secrets Kubernetes (credentials GHCR pour le pull des images, clés API pour les services)
- Application des manifests K8S avec substitution dynamique des variables (image, namespace, politique de pull, volumes)
- Redémarrage des deployments pour prendre en compte les nouvelles images

## Structure du projet

```
Projet-Agent-IA-Immo-MCP/
├── config.py              # Configuration (chemins, BDD, modèle)
├── config_agent.py        # Configuration LLM (Mistral AI)
├── pyproject.toml         # Dépendances par groupes (fastapi, mcp, dev)
├── Makefile               # Commandes courantes
├── ansible_playbook.yml   # Playbook de déploiement K3S
├── docker/
│   ├── Dockerfile.api     # Image FastAPI (multi-stage)
│   └── Dockerfile.mcp    # Image MCP (multi-stage)
├── k8s/
│   ├── fastapi-app.yaml   # Manifest Kubernetes FastAPI
│   └── mcp-server.yaml   # Manifest Kubernetes MCP
├── src/
│   ├── app/               # Application FastAPI
│   │   ├── main.py        # Point d'entrée
│   │   ├── routes.py      # Routes (predict, chat, chatbot)
│   │   ├── monitoring/    # Métriques Prometheus
│   │   └── templates/     # Templates HTML (Jinja2)
│   ├── agents/            # Client et agent MCP (LangChain)
│   │   ├── clientMCP.py   # Connexion au serveur MCP
│   │   └── agentMCP.py    # Création de l'agent
│   ├── mcp/               # Serveur MCP
│   │   ├── serverMCP.py   # Point d'entrée FastMCP
│   │   └── tools/         # Outils (geocoding, transactions, estimation, commune)
│   ├── inference/         # Logique de prédiction (model.py)
│   └── utils/             # Utilitaires (geo, chargement modèles)
├── scripts/               # Scripts (entraînement, nettoyage, déploiement)
├── notebooks/             # Notebooks d'exploration (Marimo)
├── tests/                 # Tests unitaires et d'intégration
├── monitoring/            # Dashboard Grafana
├── docs/                  # Documentation (benchmark, note de cadrage)
├── data/                  # Données (DVF, BPE INSEE DuckDB)
├── model/                 # Modèles entraînés
└── .github/workflows/     # CI/CD (tests, build, deploy)
```

## Données

Le projet utilise deux sources de données principales :

1. **Données DVF** (API DVF+ Cerema) : Transactions immobilières des 5 dernières années, interrogées en temps réel via l'API avec pagination asynchrone et cache disque (TTL 30 jours).

2. **Base Permanente des Équipements (BPE INSEE)** : Équipements par commune (écoles, commerces, infrastructures), stockés localement dans une base DuckDB.

Sources :
- [API Cerema DVF](https://www.data.gouv.fr/fr/datasets/demandes-de-valeurs-foncieres/)
- [BPE INSEE](https://www.insee.fr/fr/metadonnees/source/operation/s2216/presentation)

## Flux de Prédiction

```mermaid
sequenceDiagram
    participant U as Utilisateur
    participant FA as FastAPI
    participant MCP as Serveur MCP
    participant GEO as Geocoding API
    participant M as Modèle ML

    U->>FA: Soumet formulaire
    FA->>MCP: estimation_tools(address, type, surface, ...)
    MCP->>GEO: Géocode l'adresse
    GEO-->>MCP: Coordonnées + code INSEE
    MCP->>M: Prédiction
    M-->>MCP: Prix estimé
    MCP-->>FA: Résultat structuré
    FA-->>U: Affiche la prédiction
```

## Flux du Chatbot

```mermaid
sequenceDiagram
    participant U as Utilisateur
    participant FA as FastAPI
    participant Agent as Agent LangChain
    participant LLM as Mistral AI
    participant MCP as Serveur MCP

    U->>FA: Envoie message
    FA->>Agent: Transmet message
    Agent->>LLM: Analyse la requête
    LLM-->>Agent: Choix d'outil
    Agent->>MCP: Appelle l'outil MCP
    MCP-->>Agent: Résultat
    Agent->>LLM: Génère réponse
    LLM-->>Agent: Réponse formatée
    Agent-->>FA: Stream de la réponse
    FA-->>U: Affiche en temps réel (SSE)
```

## Configuration

- `config.py` : Chemins des données, modèle, base DuckDB
- `config_agent.py` : Configuration du LLM Mistral AI (avec retry et compatibilité MCP)
- `.env` : Clés API (MISTRAL_API_KEY, LANGSMITH_*)

## Monitoring

- **Prometheus** : Métriques exposées sur `/metrics` (latence d'inférence)
- **Grafana** : Dashboard préconfigré dans `monitoring/grafana_dashboard.json`
- **LangSmith** : Tracing de l'agent IA sur https://eu.smith.langchain.com

## License

Ce projet est sous licence MIT - voir le fichier [LICENSE](LICENSE) pour plus de détails.
