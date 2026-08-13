FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
COPY testforge/ ./testforge/
COPY tests/ ./tests/
COPY README.md ./

RUN pip install --no-cache-dir -e .

ENTRYPOINT ["testforge"]