set dotenv-load

# List available commands
default:
    @just --list

# Install all dependencies and git hooks
bootstrap:
    uv sync --group dev
    prek install
    cd frontend && npm install

# Install frontend npm dependencies
bootstrap-frontend:
    cd frontend && npm install

# Run Vite dev server with HMR on port 5173 (requires just dev running separately)
dev-frontend:
    cd frontend && npm run dev

# Build Svelte app into static/app/
build-frontend:
    cd frontend && npm run build

# Type-check frontend
check-frontend:
    cd frontend && npm run check

# Run development server with auto-reload (uses local /plonkit/ files, skips GitHub sync)
dev:
    PLONKIT_LOCAL=1 uv run uvicorn guess_explainr.app:app --reload

# Lint with ruff
lint:
    uv run ruff check .

# Fix lint errors automatically
lint-fix:
    uv run ruff check --fix .

# Check formatting
fmt-check:
    uv run ruff format --check .

# Format all files
fmt:
    uv run ruff format .

# Run type checker
typecheck:
    uv run pyrefly check

# Run tests
test *args:
    uv run pytest {{ args }}

# Run all prek hooks against every file
hooks:
    prek run --all-files

# Run lint + format check + typecheck
check: lint fmt-check typecheck

# Regenerate the Plonkit PDF guides (can take a long time; requires Docker)
pull-sources:
    docker pull minidocks/weasyprint
    cd plonkit && uv run python fetch_plonkit.py
