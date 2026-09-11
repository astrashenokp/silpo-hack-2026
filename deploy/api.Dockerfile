# Python demo API. Build from the repository root:
#   docker build -f deploy/api.Dockerfile -t smart-basket-api .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SMART_BASKET_MODE=demo

WORKDIR /srv
COPY services/api/pyproject.toml services/api/pyproject.toml
COPY services/api/src services/api/src
RUN pip install --no-cache-dir ./services/api

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2)"

# Exactly one worker: sessions, runs and operation receipts live in process memory.
CMD ["python", "-m", "uvicorn", "smart_basket.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
