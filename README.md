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
- **Flight Anomaly Detection**: Advanced pattern recognition and anomaly detection
- **Session-Based RAG**: Retrieval Augmented Generation for context-aware responses
- **Vector Database**: Qdrant integration for scalable document storage
- **Multi-Session Support**: Handle multiple users simultaneously
- **Comprehensive API**: Full REST API for all functionality

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Frontend Setup](#frontend-setup)
- [Backend Setup](#backend-setup)
- [API Usage](#api-usage)
- [Testing](#testing)
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

# Configure environment
echo "GOOGLE_API_KEY=your_google_api_key" > .env
echo "GOOGLE_MODEL_NAME=gemini-2.0-flash" >> .env

# Start backend server
python app.py
```

### 3. Access the Application
- **Frontend**: http://localhost:8080
- **Backend API**: http://localhost:8000
- **API Health Check**: http://localhost:8000/api/health

## 🎨 Frontend Setup

### Build Commands
```bash
# Development server with hot reload
npm run dev

# Production build
npm run build

# Run unit tests
npm run unit

# Run e2e tests
npm run e2e

# Run all tests
npm test
```

### Environment Variables
```bash
# Required
VUE_APP_CESIUM_TOKEN=your_cesium_ion_token

# Optional
VUE_APP_API_URL=http://localhost:8000
```

## 🔧 Backend Setup

### Installation
```bash
cd backend_api

# Install dependencies
pip install -r requirements.txt

# Or with conda
conda create -n arena python=3.10
conda activate arena
pip install -r requirements.txt
```

### Configuration
Create a `.env` file in the `backend_api` directory:

```bash
# Required
GOOGLE_API_KEY=your_google_gemini_api_key
GOOGLE_MODEL_NAME=gemini-2.0-flash

# Optional - Qdrant Vector Database
QUADRANT_URL=https://your-qdrant-url:6333
QUADRANT_API_KEY=your_qdrant_api_key

# Optional - System Configuration
API_HOST=0.0.0.0
API_PORT=8000
```

### Start Backend
```bash
# Direct start
python app.py

# With conda environment
conda activate arena
python app.py
```

## 🔌 API Usage

### Core Endpoints

#### Chat Interface
```bash
# Send message to AI
curl -X POST http://localhost:8000/api/chat \
  -H "X-Session-ID: your-session-id" \
  -H "Content-Type: application/json" \
  -d '{"message": "Analyze this flight data"}'
```

#### Flight Data Upload
```bash
# Upload flight data
curl -X POST http://localhost:8000/api/flight-data \
  -H "X-Session-ID: your-session-id" \
  -H "Content-Type: application/json" \
  -d @flight_data.json
```

#### Anomaly Detection
```bash
# Analyze flight anomalies
curl -X POST http://localhost:8000/api/anomaly/your-session-id/analyze \
  -H "Content-Type: application/json" \
  -d '{"question": "Are there any anomalies in this flight?"}'
```

### Python Client Example
```python
import requests
import uuid

# Generate session ID
session_id = str(uuid.uuid4())
headers = {'X-Session-ID': session_id}

# Upload flight data
flight_data = {
    "vehicle": "Quadcopter",
    "trajectories": {...},
    "flightModeChanges": [...],
    "events": [...]
}

response = requests.post(
    "http://localhost:8000/api/flight-data",
    headers=headers,
    json=flight_data
)

# Chat with AI
chat_response = requests.post(
    "http://localhost:8000/api/chat",
    headers=headers,
    json={"message": "What can you tell me about this flight?"}
)

print(chat_response.json()['message'])

# Analyze anomalies
anomaly_response = requests.post(
    f"http://localhost:8000/api/anomaly/{session_id}/analyze",
    json={"question": "Are there any anomalies?"}
)

print(anomaly_response.json())
```

### JavaScript/Frontend Integration
```javascript
// Generate session ID
const sessionId = 'session_' + Date.now().toString(36);

// Upload flight data
async function uploadFlightData(flightData) {
    const response = await fetch('/api/flight-data', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Session-ID': sessionId
        },
        body: JSON.stringify(flightData)
    });
    return await response.json();
}

// Chat with AI
async function chatWithAI(message) {
    const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Session-ID': sessionId
        },
        body: JSON.stringify({ message })
    });
    return await response.json();
}

// Analyze anomalies
async function analyzeAnomalies(question) {
    const response = await fetch(`/api/anomaly/${sessionId}/analyze`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ question })
    });
    return await response.json();
}
```

## 🧪 Testing

### Comprehensive Test Suite
```bash
# Run complete test suite
cd backend_api
python test_complete.py --verbose

# Run specific test categories
python test_complete.py --skip-anomaly  # Skip anomaly detection tests
python test_complete.py --skip-cleanup  # Skip cleanup tests
python test_complete.py --skip-agent    # Skip LangGraph agent tests
```

### Test Coverage
- ✅ **API Endpoints**: All 18+ endpoints tested
- ✅ **Session Management**: Multi-session handling
- ✅ **RAG Functionality**: Document storage and retrieval
- ✅ **AI Integration**: Gemini API responses
- ✅ **Anomaly Detection**: Flight data analysis
- ✅ **Error Handling**: Graceful failure handling
- ✅ **Performance**: Response time monitoring

### Manual Testing
```bash
# Health check
curl http://localhost:8000/api/health

# Check available prompts
curl http://localhost:8000/api/prompts

# List RAG collections
curl http://localhost:8000/api/rag/collections

# Get system statistics
curl http://localhost:8000/api/rag/stats
```

## 🐳 Docker Deployment

### Pre-built Image
```bash
# Run pre-built image
docker run -p 8080:8080 -d ghcr.io/ardupilot/uavlogviewer:latest
```

### Build Locally
```bash
# Build Docker image
docker build -t uavlogviewer .

# Run with environment variables
docker run -e VUE_APP_CESIUM_TOKEN=<your-token> \
           -e GOOGLE_API_KEY=<your-api-key> \
           -p 8080:8080 \
           -p 8000:8000 \
           uavlogviewer
```

### Docker Compose
```yaml
version: '3.8'
services:
  frontend:
    build: .
    ports:
      - "8080:8080"
    environment:
      - VUE_APP_CESIUM_TOKEN=${CESIUM_TOKEN}
      - VUE_APP_API_URL=http://backend:8000
  
  backend:
    build: ./backend_api
    ports:
      - "8000:8000"
    environment:
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - QUADRANT_URL=${QUADRANT_URL}
      - QUADRANT_API_KEY=${QUADRANT_API_KEY}
```

## 📚 Documentation

### Comprehensive Documentation
- **[Complete Backend Documentation](backend_api/README_COMPREHENSIVE.md)** - Full API reference and usage guide
- **[Anomaly Detection System](backend_api/README_ANOMALY_DETECTION.md)** - Flight anomaly detection capabilities
- **[Collection Management](backend_api/README_CLEANUP_SCRIPTS.md)** - Vector database management scripts

### Key Features Documentation

#### Flight Anomaly Detection
The system provides intelligent analysis of flight data to identify:
- **Sudden Changes**: Rapid altitude, velocity, or battery changes
- **Threshold Violations**: Battery voltage, temperature, altitude limits
- **Pattern Anomalies**: Unusual variance and correlations
- **Flight Phase Analysis**: Takeoff, cruise, landing patterns

#### AI Capabilities
- **Natural Language Queries**: Ask questions about flight data in plain English
- **Context-Aware Responses**: Maintains conversation context across sessions
- **Proactive Clarification**: Asks for clarification when needed
- **Internet Search**: Real-time web search for additional information

#### Vector Database
- **Qdrant Integration**: Cloud-based vector storage
- **Local Fallback**: Automatic fallback to local storage
- **Session Isolation**: Each chat session has its own collection
- **Automatic Cleanup**: Smart memory management

## 🔧 Troubleshooting

### Common Issues

#### Frontend Issues
```bash
# Clear npm cache
npm cache clean --force

# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install

# Check Cesium token
echo $VUE_APP_CESIUM_TOKEN
```

#### Backend Issues
```bash
# Check environment variables
cat backend_api/.env

# Verify API key
curl -H "Authorization: Bearer $GOOGLE_API_KEY" \
     https://generativelanguage.googleapis.com/v1/models

# Check backend health
curl http://localhost:8000/api/health
```

#### Database Issues
```bash
# Clear collections
cd backend_api
python force_cleanup.py --dry-run  # Preview
python force_cleanup.py --force    # Execute

# Check Qdrant connection
python -c "from rag_manager import get_global_rag_manager; print(get_global_rag_manager().get_manager_stats())"
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite: `python test_complete.py`
6. Submit a pull request

## 📄 License

This project is part of the ArduPilot ecosystem. See the main project repository for license information.

## 📞 Support

- **Issues**: Open an issue in the project repository
- **Documentation**: Check the comprehensive documentation in `backend_api/`
- **Testing**: Run `python test_complete.py --verbose` for diagnostics

---

**Version**: 3.0.0  
**Last Updated**: 2024-10-14  
**Compatibility**: Node.js 16+, Python 3.8+, Vue.js 2.x, Flask 2.3+
