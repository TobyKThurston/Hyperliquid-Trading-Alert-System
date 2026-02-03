#!/bin/bash
set -e

echo "Waiting for database and tables to be ready..."
python wait_for_db.py

echo "Starting worker..."
exec python -m worker.main
