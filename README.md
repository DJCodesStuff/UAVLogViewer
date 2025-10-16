# UAV Log Viewer

![log seeking](preview.gif "Logo Title Text 1")

A comprehensive JavaScript-based log viewer for MAVLink telemetry and dataflash logs with AI-powered analysis capabilities.

[Live demo here](http://plot.ardupilot.org)

## 🚀 Features

### Frontend (Vue.js)
- **Interactive Log Visualization**: Plot telemetry data with customizable graphs
- **3D Flight Path Visualization**: Cesium-based 3D flight path rendering
- **Real-time Data Processing**: Parse and display MAVLink and dataflash logs
- **Responsive UI**: Modern, mobile-friendly interface
- **AI Chat Integration**: Intelligent chat interface for flight data analysis

### Backend (Flask + AI)
- **AI-Powered Analysis**: Google Gemini LLM integration for intelligent responses
- **Session-Based RAG**: Retrieval Augmented Generation for context-aware responses
- **Vector Database**: Qdrant integration for scalable document storage
- **Multi-Session Support**: Handle multiple users simultaneously
- **Comprehensive API**: Full REST API for all functionality

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Frontend Setup](#frontend-setup)
- [Backend Setup](#backend-setup)
- [API Usage](#api-usage)
- [Docker Deployment](#docker-deployment)
- [Documentation](#documentation)

## 🚀 Quick Start

### Prerequisites
- Node.js 16+ and npm
- Python 3.8+
- Google Gemini API key

### 1. Frontend Setup
```bash
# Clone repository
git clone <repository-url>
cd UAVLogViewer

# Initialize submodules
git submodule update --init --recursive

# Install dependencies
npm install

# Set Cesium token
export VUE_APP_CESIUM_TOKEN=<your-cesium-token>

# Start development server
npm run dev
```

### 2. Backend Setup
```bash
# Navigate to backend
cd backend_api

# Install Python dependencies
pip install -r requirements.txt

# Copy environment file
cp env.example .env
# Edit .env with your API keys

# Start backend server
python app.py
```

### 3. Access the Application
- **Frontend**: http://localhost:8080
- **Backend API**: http://localhost:8000
- **API Health Check**: http://localhost:8000/api/health

## 🎨 Frontend Setup

### Environment Variables
```bash
# Required
VUE_APP_CESIUM_TOKEN=your_cesium_ion_token
```

### Build Commands
```bash
npm run dev    # Development server
npm run build  # Production build
npm test       # Run tests
```

## 🔧 Backend Setup

### Installation & Configuration
```bash
cd backend_api

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp env.example .env
# Edit .env with your API keys
```

**Required Environment Variables:**
```bash
GOOGLE_API_KEY=your_google_gemini_api_key
GOOGLE_MODEL_NAME=gemini-2.0-flash
QDRANT_URL=https://your-qdrant-url:6333
QDRANT_API_KEY=your_qdrant_api_key
```

### Deployment Options
```bash
# Development
python app.py

# Production with Gunicorn
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

## 🔌 API Usage

### Core Endpoints

```bash
# Chat with AI
curl -X POST http://localhost:8000/api/chat \
  -H "X-Session-ID: your-session-id" \
  -H "Content-Type: application/json" \
  -d '{"message": "Analyze this flight data"}'

# Upload flight data
curl -X POST http://localhost:8000/api/flight-data \
  -H "X-Session-ID: your-session-id" \
  -H "Content-Type: application/json" \
  -d @flight_data.json
```


### Python Example
```python
import requests
import uuid

session_id = str(uuid.uuid4())
headers = {'X-Session-ID': session_id}

# Upload flight data
flight_data = {"vehicle": "Quadcopter", "trajectories": {...}}
requests.post("http://localhost:8000/api/flight-data", headers=headers, json=flight_data)

# Chat with AI
response = requests.post("http://localhost:8000/api/chat", headers=headers, 
                        json={"message": "What can you tell me about this flight?"})
print(response.json()['message'])
```

## 🐳 Docker Deployment

```bash
# Run pre-built image
docker run -p 8080:8080 -d ghcr.io/ardupilot/uavlogviewer:latest
```

## 📚 Documentation

**[Backend Deployment Guide](backend_api/README.md)** - Deployment instructions
**[Detailed Backend Documentation](backend_api/README_DETAILED.md)** - Full API reference


## 📄 License

This project is part of the ArduPilot ecosystem. See the main project repository for license information.

## 📞 Support

- **Issues**: Open an issue in the project repository
- **Documentation**: Check the comprehensive documentation in `backend_api/`

---

**Version**: 3.0.0  
**Last Updated**: 2024-10-14  
**Compatibility**: Node.js 16+, Python 3.8+, Vue.js 2.x, Flask 2.3+
