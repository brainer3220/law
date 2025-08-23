.PHONY: setup install dev start rag test lint format docker-up

setup:
	python manage.py setup

install:
	python manage.py install

dev:
	python manage.py install --dev

start:
	python manage.py start

rag:
	python manage.py start

test:
	uv run python -m pytest -v

lint:
	python manage.py lint

format:
	python manage.py format

docker-up:
	docker compose up --build
