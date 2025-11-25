#!/bin/bash

# Check if .venv is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Virtual environment not detected."
    if [ -d ".venv" ]; then
        echo "🔄 Activating .venv..."
        source .venv/bin/activate
    else
        echo "❌ .venv directory not found. Please setup the environment first."
        exit 1
    fi
fi

# Run the app
echo "🚀 Launching ShouldISignThis? Demo..."
export PYTHONPATH=$PYTHONPATH:.
streamlit run shouldisignthis/app.py
