.PHONY: migrate revision downgrade test

migrate:
	cd api && uv run alembic -c alembic.ini upgrade head

revision:
	cd api && uv run alembic -c alembic.ini revision --autogenerate -m "$(name)"

downgrade:
	cd api && uv run alembic -c alembic.ini downgrade -1

test:
	cd api && uv run --extra dev pytest tests/ -v
