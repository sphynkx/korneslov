#!/bin/sh
cd "$(dirname "$0")"
source .venv/bin/activate
python webhook.py
