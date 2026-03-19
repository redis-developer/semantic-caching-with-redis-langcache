MAKEFLAGS += --no-print-directory

## ---------------------------------------------------------------------------
## | The purpose of this Makefile is to provide all the functionality needed |
## | to install, develop, build, and run this app.                           |
## ---------------------------------------------------------------------------

help:              ## Show this help
	@sed -ne '/@sed/!s/## //p' $(MAKEFILE_LIST)

install:           ## Install all dependencies
	@uv sync --all-extras

dev:               ## Run a dev server and watch files to restart
	@$(MAKE) install
	@uv run fastapi dev src/app/main.py --port $${PORT:-8080}

serve:             ## Run a production server
	@$(MAKE) install
	@uv run fastapi run src/app/main.py --port $${PORT:-8080}

test:              ## Run tests
	@$(MAKE) install
	@uv run pytest -rxP

docker:            ## Spin down docker containers and then rebuild and run them
	@docker compose down
	@docker compose up -d --build

format:            ## Format code
	@$(MAKE) install
	@uv run ruff check src/app __test__ --fix
	@uv run ruff format src/app __test__

lint:              ## Lint code
	@$(MAKE) install
	@uv run ruff check src/app __test__
	@uv run mypy src/app

lock:              ## Update lock file
	@$(MAKE) install
	@uv lock

update:            ## Update dependencies
	@$(MAKE) install
	@uv sync --upgrade

clean:             ## Remove build files
	@rm -rf .venv/ .mypy_cache/ .ruff_cache/ .pytest_cache/
	@find . -type d -name __pycache__ -exec rm -r {} \+
