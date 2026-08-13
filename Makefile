.PHONY: test test-offline install

install:
	pip install -e .

test:
	python -m pytest tests/ -v

test-offline:
	python -m pytest tests/ -v -m "not integration"