#!/bin/bash

# Test script for arena conda environment

echo "Testing arena conda environment for UAV Log Viewer Backend..."

# Activate arena environment
echo "Activating arena conda environment..."
source ~/anaconda3/etc/profile.d/conda.sh
conda activate arena

# Check environment
echo "Current conda environment: $CONDA_DEFAULT_ENV"
echo "Python path: $(which python)"

# Test imports
echo ""
echo "Testing imports..."

python -c "
try:
    import flask
    print('✓ Flask:', flask.__version__)
except ImportError as e:
    print('✗ Flask:', e)

try:
    import langchain
    print('✓ LangChain:', langchain.__version__)
except ImportError as e:
    print('✗ LangChain:', e)

try:
    import qdrant_client
    print('✓ Qdrant Client:', qdrant_client.__version__)
except ImportError as e:
    print('✗ Qdrant Client:', e)

try:
    import google.generativeai
    print('✓ Google Generative AI')
except ImportError as e:
    print('✗ Google Generative AI:', e)

try:
    from dotenv import load_dotenv
    print('✓ python-dotenv')
except ImportError as e:
    print('✗ python-dotenv:', e)
"

# Test backend import
echo ""
echo "Testing backend import..."
python -c "
try:
    from app import app
    print('✓ Backend imports successfully')
except Exception as e:
    print('✗ Backend import failed:', e)
"

echo ""
echo "Test complete!"
