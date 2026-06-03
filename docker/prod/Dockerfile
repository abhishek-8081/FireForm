FROM python:3.11-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    libgl1 \
    libglib2.0-0 \
    libxcb1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

# Copy only app code, not data/ temp/ tests/ docs/ etc.
COPY app/ ./app/
COPY requirements.txt .

ENV PYTHONPATH=/app

# Data dirs created here; actual storage comes from mounted volumes at runtime.
RUN mkdir -p /data/db /data/uploads && chmod +x /entrypoint.sh

EXPOSE 8000

CMD ["gunicorn", "app.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
