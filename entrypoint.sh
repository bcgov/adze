#!/bin/bash
set -e

echo "🛠 MODE = ${MODE}"

if [ "$MODE" = "web" ]; then
  echo "🚀 Starting Flask server..."
  flask run --host=0.0.0.0 --port=5000

elif [ "$MODE" = "cli" ]; then
  echo "⚙️  Running CLI conversion..."
  ./run_script_oc.sh

else
  echo "❌ Unknown MODE: $MODE"
  exit 1
fi
