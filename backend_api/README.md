# UAV Log Viewer Backend API - Deployment Guide

A Flask-based REST API powering the UAV Log Viewer with AI-assisted analysis, session-scoped RAG (Qdrant), and modular telemetry tooling for MAVLink/Dataflash/DJI logs.

## 📋 Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
- [Deployment Options](#deployment-options)
- [Environment Setup](#environment-setup)
- [Troubleshooting](#troubleshooting)

## 🛠 Installation

### Prerequisites
- Python 3.8+
- Google Gemini API key
- Qdrant Vector Database access

### Setup

1. **Install Dependencies**
```bash
cd backend_api
pip install -r requirements.txt
```

2. **Environment Configuration**
The backend includes a reference environment file (`env.example`) with all available configuration options.

**Quick Setup:**
```bash
cd backend_api

# Copy the reference environment file
cp env.example .env

# Edit the .env file with your configuration
nano .env  # or use your preferred editor
```

**Required Configuration:**
```bash
# Required - Google Gemini API
GOOGLE_API_KEY=your_google_gemini_api_key
GOOGLE_MODEL_NAME=gemini-2.0-flash

# Required - Qdrant Vector Database (for RAG functionality)
QDRANT_URL=https://your-qdrant-url:6333
QDRANT_API_KEY=your_qdrant_api_key
```

**Optional Configuration:**
```bash
# API Settings
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=True

# CORS Settings (for frontend integration)
CORS_ORIGINS=http://localhost:8080,http://0.0.0.0:8080

# Session Settings
SESSION_TIMEOUT_HOURS=24
MAX_SESSIONS=100

# Logging
LOG_LEVEL=INFO
```

**Environment File Reference:**
The `backend_api/env.example` file contains all available configuration options with descriptions. Copy this file to `.env` and customize the values for your deployment.

## 🚀 Deployment Options

### Option 1: Direct Python Deployment
```bash
cd backend_api
python app.py
```

### Option 2: Production Deployment with Gunicorn
```bash
cd backend_api

# Install gunicorn
pip install gunicorn

# Run with gunicorn (production)
gunicorn -w 4 -b 0.0.0.0:8000 app:app

# Run with gunicorn (development)
gunicorn -w 1 -b 0.0.0.0:8000 --reload app:app
```

### Option 3: Using the Start Script
```bash
cd backend_api
python start_api.py
```

## 🔧 Maintenance

### Cleanup Qdrant Collections
```bash
cd backend_api
python force_cleanup.py --dry-run   # preview
python force_cleanup.py --force     # delete all collections
```

### Health Check
```bash
curl http://localhost:8000/api/health
```

## 🔧 Environment Setup

### Required Environment Variables

Create a `.env` file in the `backend_api` directory with the following variables:

```bash
# Google Gemini API Configuration
GOOGLE_API_KEY=your_google_gemini_api_key
GOOGLE_MODEL_NAME=gemini-2.0-flash

# Qdrant Vector Database Configuration
QDRANT_URL=https://your-qdrant-url:6333
QDRANT_API_KEY=your_qdrant_api_key

# API Settings
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=True

# CORS Settings (for frontend integration)
CORS_ORIGINS=http://localhost:8080,http://0.0.0.0:8080

# Session Settings
SESSION_TIMEOUT_HOURS=24
MAX_SESSIONS=100

# Logging
LOG_LEVEL=INFO
```

### Environment File Reference

The `backend_api/env.example` file contains all available configuration options with descriptions. Copy this file to `.env` and customize the values for your deployment:

```bash
cp env.example .env
```

**Version**: 2.0.0  
**Last Updated**: 2024-01-01  
**Compatibility**: Python 3.8+, Flask 2.3+, Google Gemini API