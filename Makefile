.PHONY: db-up db-down db-reset download verify-raw inspect ingest rebuild-indexes discover-assets download-assets verify-assets dev build

# Database
db-up:
	docker compose up -d

db-down:
	docker compose down

db-reset:
	docker compose down -v && docker compose up -d

# Data mirror
download:
	python scripts/ingest/download_manifest_and_files.py

verify-raw:
	python scripts/ingest/verify_raw_files.py

inspect:
	python scripts/ingest/inspect_schemas.py

# Ingestion
ingest:
	python scripts/ingest/load_structured_data.py

rebuild-indexes:
	python scripts/ingest/rebuild_search_indexes.py

# Assets
discover-assets:
	python scripts/assets/discover_assets.py

download-assets:
	python scripts/assets/download_assets.py

verify-assets:
	python scripts/assets/verify_assets.py

# App
dev:
	pnpm dev

build:
	pnpm build

# Full pipeline
all: db-up download verify-raw ingest rebuild-indexes discover-assets
	@echo "Full pipeline complete."
