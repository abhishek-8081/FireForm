# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app

# Use apt cache mount to speed up system package installation across builds
RUN rm -f /etc/apt/apt.conf.d/docker-clean; echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt \
    apt-get update && apt-get install -y \
    curl \
    libgl1 \
    libglib2.0-0 \
    libxcb1

COPY requirements.txt .

# Use pip cache mount so it remembers downloaded wheels
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
