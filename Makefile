.PHONY: install dev api app test lint docker-up docker-down

install:
	pip install -r requirements.txt

dev:
	pip install -r requirements-dev.txt

api:
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

app:
	streamlit run app.py

test:
	pytest tests/ -v --tb=short

lint:
	ruff check summarizer/ api/ tests/
	mypy summarizer/ api/ --ignore-missing-imports

docker-up:
	docker-compose up --build

docker-down:
	docker-compose down -v

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null; true
	find . -name "*.pyc" -delete
