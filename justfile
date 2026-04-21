set dotenv-load

# List available commands
default:
    @just --list

# Install all dependencies and git hooks
bootstrap:
    uv sync --group dev
    prek install

# Run development server with auto-reload
dev:
    uv run uvicorn geolearnr.app:app --reload

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