#!/bin/bash

# Helper script to create .env file

echo "Creating .env file for UAV Log Viewer Backend..."
echo ""

# Check if .env already exists
if [ -f .env ]; then
    echo "⚠️  Warning: .env file already exists!"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cancelled. Existing .env file kept."
        exit 0
    fi
fi

# Ask for API key
echo "Please enter your Google Gemini API Key:"
echo "(Get one at: https://aistudio.google.com/app/apikey)"
read -p "API Key: " api_key

if [ -z "$api_key" ]; then
    echo "❌ Error: API key cannot be empty"
    exit 1
fi

# Ask for Qdrant Cloud (optional)
echo ""
echo "Optional: Qdrant Cloud configuration (for documentation search)"
echo "Leave blank to skip"
read -p "Qdrant URL: " qdrant_url
read -p "Qdrant API Key: " qdrant_api_key

# Create .env file
cat > .env << EOF
# Google Gemini API
GOOGLE_API_KEY=$api_key

# Qdrant Cloud Configuration (optional)
QDRANT_URL=$qdrant_url
QDRANT_API_KEY=$qdrant_api_key

# Flask Configuration
FLASK_PORT=8000
FLASK_DEBUG=True

# Session Configuration
SESSION_TIMEOUT=3600

# Agent Configuration
MAX_AGENT_ITERATIONS=5
EOF

echo ""
echo "✅ .env file created successfully!"
echo ""
echo "Next steps:"
echo "  1. Install dependencies: pip install -r requirements.txt"
echo "  2. Start the API: ./start_api.sh"
echo ""

