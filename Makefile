.PHONY: install backend-migrate seed backend-test frontend-check frontend-build check

install:
	python -m pip install -e "backend[dev]"
	cd frontend && npm install

backend-migrate:
	cd backend && python -m alembic upgrade head

seed:
	python scripts/seed_demo.py

backend-test:
	cd backend && python -m pytest -q

frontend-check:
	cd frontend && npm run type-check

frontend-build:
	cd frontend && npm run build

check: backend-test frontend-check frontend-build

