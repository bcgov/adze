#!/bin/bash
set -e

echo "🛠 MODE = ${MODE}"

echo "🚀 Starting Flask server..."
flask run --host=0.0.0.0 --port=5000
