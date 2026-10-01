#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -o errexit

# Upgrade pip and install all production dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Run database synchronization and demo seeding
python seed.py
