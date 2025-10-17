#!/bin/bash

# UAV Log Viewer Backend API Startup Script

echo "Starting UAV Log Viewer Backend API..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    echo "Please create a .env file based on .env.example"
    echo ""
    echo "Quick setup:"
    echo "  1. Copy .env.example to .env"
    echo "  2. Add your GOOGLE_API_KEY"
    echo ""
    exit 1
fi

# Activate arena conda environment
echo "Activating arena conda environment..."
source ~/anaconda3/etc/profile.d/conda.sh
conda activate arena

# Check if arena environment is active
if [ "$CONDA_DEFAULT_ENV" != "arena" ]; then
    echo "Error: Could not activate arena conda environment"
    echo "Please ensure arena environment exists: conda create -n arena python=3.10"
    exit 1
fi

echo "✓ Using arena conda environment: $CONDA_DEFAULT_ENV"

# Check if requirements are installed
python -c "import flask, langchain, qdrant_client, google.generativeai" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing missing requirements..."
    pip install -r requirements.txt
fi

# Start the Flask app
echo "Starting Flask API on port 8000..."
echo "Access at: http://localhost:8000"
echo ""

python app.py

