# syntax=docker/dockerfile:1

FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --target=/deps -r requirements.txt

FROM python:3.11-slim

WORKDIR /app

RUN useradd --create-home --shell /bin/bash appuser
RUN mkdir -p /app/models /app/runs /app/data && chown -R appuser:appuser /app/models /app/runs /app/data

COPY --from=builder /deps /usr/local/lib/python3.11/site-packages/
COPY trading_lstm_rl_app.py .

ENV PYTHONUNBUFFERED=1
ENV TRADING_APP_PORT=8080

EXPOSE 8080

USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080', timeout=3)" || exit 1

CMD ["python", "trading_lstm_rl_app.py"]