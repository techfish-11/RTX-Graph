FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CONFIG_PATH=/app/config.yaml \
    DATA_DIR=/app/data \
    WEB_PORT=8080

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends rrdtool ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY templates ./templates
COPY static ./static
COPY config.yaml ./config.yaml

RUN mkdir -p /app/data

EXPOSE 8080

CMD ["python", "-m", "app.main"]
