#!/bin/sh
set -e

# Ensure data directories exist (volumes may be empty on first run)
mkdir -p /data/db /data/uploads

# Run DB migrations / init before starting the server
python3 -m app.db.init_db

exec "$@"
