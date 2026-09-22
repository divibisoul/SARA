FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md /app/
COPY src /app/src
COPY scripts /app/scripts
COPY tests /app/tests

RUN pip install --no-cache-dir -e ".[dev]"

CMD ["python", "scripts/run_regenerative_loop.py"]
