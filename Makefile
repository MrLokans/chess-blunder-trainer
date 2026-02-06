SHELL := /bin/sh
.DEFAULT_GOAL := help

# Tools
UV := uv
UV_SYNC_FLAGS := --frozen

# Common options
DATA_DIR := data
USERNAME :=
SOURCE :=

# Engine options
ENGINE_PATH :=
DEPTH := 14
TIME :=

# Server options
HOST := 127.0.0.1
PORT := 8000

# Fetch options
MAX :=
BATCH_SIZE := 200

# Other options
LIMIT :=
GAME_ID :=
RESET :=
FORCE :=

.PHONY: help install install-dev cli clean
.PHONY: fetch-lichess fetch-chesscom list show index
.PHONY: analyze analyze-bulk train-ui
.PHONY: format lint lint/be lint/fe check test test/be test/fe download-pieces migrate
.PHONY: docker/build docker/run docker/stop

help: ## Show available targets
	@awk 'BEGIN {FS = ":.*##"; print "Available targets:"} \
		/^[a-zA-Z_\/-]+:.*##/ {printf "  %-16s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies
	$(UV) sync $(UV_SYNC_FLAGS)

install-dev: ## Install with dev dependencies
	$(UV) sync --all-extras $(UV_SYNC_FLAGS)

cli: ## Run CLI with custom args (usage: make cli ARGS="list")
	@test -n "$(ARGS)" || (echo "Error: ARGS required" && exit 1)
	$(UV) run blunder-tutor $(ARGS)

# Fetch commands
fetch-lichess: ## Fetch from Lichess (usage: make fetch-lichess USERNAME=player)
	@test -n "$(USERNAME)" || (echo "Error: USERNAME required" && exit 1)
	$(UV) run blunder-tutor fetch lichess $(USERNAME) --data-dir $(DATA_DIR) \
		$(if $(MAX),--max $(MAX)) \
		$(if $(BATCH_SIZE),--batch-size $(BATCH_SIZE))

fetch-chesscom: ## Fetch from Chess.com (usage: make fetch-chesscom USERNAME=player)
	@test -n "$(USERNAME)" || (echo "Error: USERNAME required" && exit 1)
	$(UV) run blunder-tutor fetch chesscom $(USERNAME) --data-dir $(DATA_DIR) \
		$(if $(MAX),--max $(MAX))

# Game management
list: ## List games (optional: SOURCE, USERNAME, LIMIT)
	$(UV) run blunder-tutor list --data-dir $(DATA_DIR) \
		$(if $(SOURCE),--source $(SOURCE)) \
		$(if $(USERNAME),--username $(USERNAME)) \
		$(if $(LIMIT),--limit $(LIMIT))

show: ## Show game details (usage: make show GAME_ID=abc123)
	@test -n "$(GAME_ID)" || (echo "Error: GAME_ID required" && exit 1)
	$(UV) run blunder-tutor show $(GAME_ID) --data-dir $(DATA_DIR)

index: ## Rebuild index (optional: SOURCE, USERNAME, RESET=1)
	$(UV) run blunder-tutor index --data-dir $(DATA_DIR) \
		$(if $(SOURCE),--source $(SOURCE)) \
		$(if $(USERNAME),--username $(USERNAME)) \
		$(if $(RESET),--reset)

# Analysis commands
analyze: ## Analyze single game (usage: make analyze GAME_ID=abc123)
	@test -n "$(GAME_ID)" || (echo "Error: GAME_ID required" && exit 1)
	$(UV) run blunder-tutor analyze $(GAME_ID) --data-dir $(DATA_DIR) \
		$(if $(ENGINE_PATH),--engine-path $(ENGINE_PATH)) \
		$(if $(TIME),--time $(TIME),--depth $(DEPTH))

analyze-bulk: ## Analyze multiple games (optional: SOURCE, USERNAME, LIMIT, FORCE=1)
	$(UV) run blunder-tutor analyze-bulk --data-dir $(DATA_DIR) \
		$(if $(ENGINE_PATH),--engine-path $(ENGINE_PATH)) \
		$(if $(TIME),--time $(TIME),--depth $(DEPTH)) \
		$(if $(SOURCE),--source $(SOURCE)) \
		$(if $(USERNAME),--username $(USERNAME)) \
		$(if $(LIMIT),--limit $(LIMIT)) \
		$(if $(FORCE),--force)

# Training UI
train-ui: ## Start training UI (usage: make train-ui USERNAME=player)
	$(UV) run blunder_tutor train-ui \
		$(if $(ENGINE_PATH),--engine-path $(ENGINE_PATH)) \
		$(if $(TIME),--time $(TIME),--depth $(DEPTH)) \
		--host $(HOST) --port $(PORT) \
		$(if $(SOURCE),--source $(SOURCE))

# Setup
download-pieces: ## Download chess piece images
	$(UV) run python blunder_tutor/scripts/download_pieces.py

# Database
migrate: ## Run database migrations
	$(UV) run blunder-tutor-db

# Code quality
lint: lint/be lint/fe ## Lint all code

lint/be: ## Lint Python with ruff
	$(UV) run ruff check blunder_tutor/ main.py

lint/fe: ## Lint JavaScript with ESLint
	npx eslint blunder_tutor/web/static/js/

fix: ## Auto-fix linting issues
	$(UV) run ruff format
	$(UV) run ruff check --fix --unsafe-fixes blunder_tutor/ main.py
	npx eslint blunder_tutor/web/static/js/ --fix

test: test/be test/fe ## Run all tests

test/be: ## Run Python tests with pytest
	$(UV) run pytest tests/ -v

test/fe: ## Run JavaScript tests with Node test runner
	node --test 'tests_fe/test_*.js'

# Docker
DOCKER_IMAGE := blunder-tutor
DOCKER_TAG := dev
DOCKER_PLATFORM :=

docker/build: ## Build Docker image (optional: DOCKER_TAG=dev, DOCKER_PLATFORM=linux/amd64)
	DOCKER_BUILDKIT=1 docker build \
		$(if $(DOCKER_PLATFORM),--platform $(DOCKER_PLATFORM)) \
		-t $(DOCKER_IMAGE):$(DOCKER_TAG) \
		--build-arg STOCKFISH_VERSION=sf_17 \
		--progress=plain \
		.

docker/run: ## Run Docker container (optional: DOCKER_TAG=dev)
	docker run --rm -it \
		-p $(PORT):8000 \
		-v $(PWD)/data:/app/data \
		$(if $(LICHESS_USERNAME),-e LICHESS_USERNAME=$(LICHESS_USERNAME)) \
		$(if $(CHESSCOM_USERNAME),-e CHESSCOM_USERNAME=$(CHESSCOM_USERNAME)) \
		$(DOCKER_IMAGE):$(DOCKER_TAG)

docker/stop: ## Stop running container
	-docker stop $$(docker ps -q --filter ancestor=$(DOCKER_IMAGE):$(DOCKER_TAG))

# Cleanup
clean: ## Remove Python cache files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
