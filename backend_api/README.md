# UAV Log Viewer Backend API

A comprehensive Flask-based REST API that provides intelligent chat functionality for the UAV Log Viewer frontend. The backend features AI-powered responses using Google Gemini, session-based RAG (Retrieval Augmented Generation), smart vector database management, and modular architecture for scalable UAV flight data analysis.

## 🚀 Features

### Core Functionality
- **Multi-Session Support**: Handle multiple users simultaneously with unique session IDs
- **AI-Powered Chat**: Google Gemini LLM integration for intelligent, context-aware responses
- **Flight Data Integration**: Store and analyze flight data from uploaded log files
- **Session-Based RAG**: Each chat session maintains its own document collection
- **Smart Vector Database**: Automatic collection lifecycle management with cleanup
- **Text Sanitization**: Clean, plain text output without special characters
- **Modular Architecture**: Extensible design for future enhancements

### Advanced Features
- **LangGraph React Agent**: Implements ReAct pattern for intelligent tool usage
- **Flexible System Prompts**: Switch between different AI personalities
- **Automatic Cleanup**: Smart memory management with configurable TTL
- **Persistent Storage**: Collections saved to disk and restored on restart
- **Comprehensive API**: Full CRUD operations for collections and sessions
- **Health Monitoring**: System statistics and health checks

## 📋 Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
- [API Endpoints](#api-endpoints)
- [Architecture](#architecture)
- [Usage Examples](#usage-examples)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

## 🛠 Installation

### Prerequisites
- Python 3.8+
- Google Gemini API key

### Setup

1. **Install Dependencies**
```bash
pip install -r requirements.txt
```

2. **Environment Configuration**
Create a `.env` file in the backend_api directory:
```bash
# Required
GOOGLE_API_KEY=your_google_api_key_here

# Optional
GOOGLE_MODEL_NAME=gemini-pro
SYSTEM_PROMPT=custom_prompt_here
API_HOST=0.0.0.0
API_PORT=8000
```

3. **Start the Backend**
```bash
python app.py
```

The API will start on `http://localhost:8000`

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `GOOGLE_API_KEY` | Google Gemini API key | - | ✅ |
| `GOOGLE_MODEL_NAME` | Gemini model name | `gemini-pro` | ❌ |
| `SYSTEM_PROMPT` | Default system prompt | ArduPilot analyst | ❌ |
| `API_HOST` | API host address | `0.0.0.0` | ❌ |
| `API_PORT` | API port | `8000` | ❌ |

### Vector Database Settings

Qdrant is mandatory. Set these environment variables:

```
QDRANT_URL=<your_qdrant_url>
QDRANT_API_KEY=<your_api_key>
```

## 🔧 Maintenance

Cleanup all Qdrant collections:

```bash
cd backend_api
python force_cleanup.py --dry-run   # preview
python force_cleanup.py --force     # delete all collections
```

## 🔌 API Endpoints

### Core Chat Endpoints

#### 1. Chat Endpoint
**POST** `/api/chat`

Send messages to the AI chat interface.

**Headers:**
- `X-Session-ID`: Unique session identifier
- `Content-Type`: application/json

**Request Body:**
```json
{
    "message": "What flight modes were used in this flight?",
    "sessionId": "session_xxx",
    "timestamp": 1234567890
}
```

**Response:**
```json
{
    "message": "Based on your flight data, I can see your vehicle used 3 different flight modes: STABILIZE, AUTO, and RTL. The flight started in STABILIZE mode, switched to AUTO for the mission, and ended with RTL for return to launch.",
    "session_id": "session_xxx",
    "timestamp": "2024-01-01T12:00:00"
}
```

#### 2. Flight Data Storage
**POST** `/api/flight-data`

Store flight data for a session (called by frontend when log is processed).

**Headers:**
- `X-Session-ID`: Unique session identifier
- `Content-Type`: application/json

**Request Body:**
```json
{
    "vehicle": "Copter",
    "trajectories": {...},
    "flightModeChanges": [...],
    "events": [...],
    "metadata": {...}
}
```

**Response:**
```json
{
    "success": true,
    "session_id": "session_xxx",
    "data_summary": {
        "has_flight_data": true,
        "vehicle_type": "Copter",
        "gps_points": 1250,
        "altitude_range": {"min": 0, "max": 150.5},
        "flight_modes": ["STABILIZE", "AUTO", "RTL"]
    },
    "available_data_types": ["GPS Data", "Flight Modes", "Events"],
    "rag_status": "Added 1 document(s) to session session_xxx. Total documents: 1",
    "message": "Flight data stored successfully"
}
```

### Session Management

#### 3. Session Information
**GET** `/api/session/{session_id}`

Get detailed information about a specific session.

**Response:**
```json
{
    "session_id": "session_xxx",
    "created_at": "2024-01-01T12:00:00",
    "last_activity": "2024-01-01T12:05:00",
    "message_count": 5,
    "data_summary": {...},
    "available_data_types": [...],
    "has_flight_data": true
}
```

#### 4. List All Sessions
**GET** `/api/sessions`

Get information about all active sessions.

**Response:**
```json
{
    "sessions": [
        {
            "session_id": "session_xxx",
            "created_at": "2024-01-01T12:00:00",
            "last_activity": "2024-01-01T12:05:00",
            "message_count": 5,
            "has_flight_data": true,
            "vehicle_type": "Copter",
            "flight_modes_count": 3
        }
    ],
    "total_sessions": 1
}
```

### RAG System Management

#### 5. List RAG Collections
**GET** `/api/rag/collections`

List all vector database collections.

**Response:**
```json
{
    "collections": [
        {
            "collection_id": "uuid-here",
            "session_id": "session_xxx",
            "name": "Session_session_xxx",
            "status": "active",
            "document_count": 5,
            "created_at": "2024-01-01T12:00:00",
            "last_accessed": "2024-01-01T12:05:00"
        }
    ],
    "total_collections": 1
}
```

#### 6. Collection Status
**GET** `/api/rag/collections/{session_id}`

Get status of a specific session's collection.

**Response:**
```json
{
    "session_id": "session_xxx",
    "collection_id": "uuid-here",
    "status": "active",
    "document_count": 5,
    "has_documents": true,
    "created_at": "2024-01-01T12:00:00",
    "last_accessed": "2024-01-01T12:05:00",
    "name": "Session_session_xxx",
    "description": null,
    "tags": []
}
```

#### 7. Clear Collection
**POST** `/api/rag/collections/{session_id}/clear`

Clear all documents from a session's collection.

**Response:**
```json
{
    "success": true,
    "message": "Cleared collection for session session_xxx"
}
```

#### 8. Delete Collection
**DELETE** `/api/rag/collections/{session_id}`

Delete a session's collection entirely.

**Response:**
```json
{
    "success": true,
    "message": "Deleted collection for session session_xxx"
}
```

#### 9. RAG System Statistics
**GET** `/api/rag/stats`

Get comprehensive RAG system statistics.

**Response:**
```json
{
    "total_collections": 5,
    "active_collections": 3,
    "archived_collections": 2,
    "total_documents": 15,
    "max_collections": 50,
    "collection_ttl_hours": 24,
    "auto_cleanup_enabled": true
}
```

#### 10. Manual Cleanup
**POST** `/api/rag/cleanup`

Manually trigger cleanup of old collections.

**Response:**
```json
{
    "success": true,
    "message": "Cleanup completed"
}
```

### System Management

#### 11. Health Check
**GET** `/api/health`

Check API health and system status.

**Response:**
```json
{
    "status": "healthy",
    "timestamp": "2024-01-01T12:00:00",
    "active_sessions": 2,
    "cached_flight_data": 2,
    "llm_agent_available": true
}
```

#### 12. System Prompts
**GET** `/api/prompts`

List all available system prompts.

**Response:**
```json
{
    "available_prompts": [
        "ardupilot_analyst",
        "uav_log_analysis", 
        "flight_data_expert"
    ],
    "total_prompts": 3
}
```

#### 13. Update System Prompt
**POST** `/api/prompt/{session_id}`

Switch system prompt for a specific session.

**Request Body:**
```json
{
    "prompt_name": "flight_data_expert"
}
```

**Response:**
```json
{
    "success": true,
    "session_id": "session_xxx",
    "prompt_name": "flight_data_expert",
    "message": "System prompt updated to: flight_data_expert"
}
```

## 🏗 Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    UAV Log Viewer Backend                   │
├─────────────────────────────────────────────────────────────┤
│  Flask API Server (app.py)                                 │
│  ├── Session Manager                                        │
│  ├── Chat Endpoints                                         │
│  └── RAG Management Endpoints                               │
├─────────────────────────────────────────────────────────────┤
│  LangGraph React Agent (llm_config.py)                     │
│  ├── Google Gemini Integration                              │
│  ├── ReAct Pattern Implementation                           │
│  └── Tool Integration                                       │
├─────────────────────────────────────────────────────────────┤
│  Modular RAG System (in_memory_rag.py)                     │
│  ├── Session-Based Collections                              │
│  ├── BM25 Search Engine                                     │
│  └── Document Management                                    │
├─────────────────────────────────────────────────────────────┤
│  Smart Vector DB Manager (vector_db_manager.py)            │
│  ├── Collection Lifecycle Management                        │
│  ├── Automatic Cleanup                                      │
│  └── Persistent Storage                                     │
├─────────────────────────────────────────────────────────────┤
│  Text Processing (text_utils.py)                           │
│  ├── Text Sanitization                                      │
│  ├── Special Character Filtering                            │
│  └── Flight Data Formatting                                 │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Flight Data Upload**
   ```
   Frontend → POST /api/flight-data → Session Manager → RAG System → Vector DB
   ```

2. **Chat Interaction**
   ```
   Frontend → POST /api/chat → Session Manager → LangGraph Agent → Gemini API → Response
   ```

3. **RAG Retrieval**
   ```
   User Query → RAG Search → Relevant Documents → Context Enhancement → AI Response
   ```

### Session Management

Each session maintains:
- **Unique Session ID**: UUID-based identifier
- **Chat History**: Conversation messages
- **Flight Data**: Processed log data
- **RAG Collection**: Document storage and retrieval
- **LLM Agent**: Dedicated AI agent instance
- **Context**: Flight data summary and metadata

## 💡 Usage Examples

### Python Client Example

```python
import requests
import uuid

# Generate session ID
session_id = str(uuid.uuid4())

# Store flight data
flight_data = {
    "vehicle": "Quadcopter",
    "trajectories": {
        "GPS": {
            "trajectory": [[-122.4194, 37.7749, 100, 1234567890]],
            "timeTrajectory": {1234567890: [-122.4194, 37.7749, 100, 1234567890]}
        }
    },
    "flightModeChanges": [[1234567890, "STABILIZE"], [1234567891, "AUTO"]],
    "events": [[1234567890, "ARMED"]],
    "metadata": {"startTime": "2024-01-01T12:00:00"}
}

response = requests.post(
    "http://localhost:8000/api/flight-data",
    headers={"X-Session-ID": session_id},
    json=flight_data
)

print(f"Flight data stored: {response.json()['success']}")

# Chat with AI
chat_response = requests.post(
    "http://localhost:8000/api/chat",
    headers={"X-Session-ID": session_id},
    json={"message": "What can you tell me about this flight?"}
)

print(f"AI Response: {chat_response.json()['message']}")

# Check RAG status
rag_status = requests.get(
    f"http://localhost:8000/api/rag/collections/{session_id}"
)

print(f"Documents in collection: {rag_status.json()['document_count']}")
```

### JavaScript/Frontend Integration

```javascript
// Generate session ID
const sessionId = 'session_' + Date.now().toString(36);

// Store flight data
async function storeFlightData(flightData) {
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

// Send chat message
async function sendChatMessage(message) {
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

// Usage
const flightData = {
    vehicle: "Quadcopter",
    trajectories: {...},
    flightModeChanges: [...],
    // ... other flight data
};

await storeFlightData(flightData);
const chatResponse = await sendChatMessage("Analyze this flight data");
console.log(chatResponse.message);
```

## 🧪 Testing

### Run Test Suite

```bash
# Start the backend
python app.py

# In another terminal, run tests
python test_api.py
python test_flexible_chat.py
python test_langgraph_agent.py
python test_prompts.py
```

### Test Coverage

- ✅ **API Endpoints**: All endpoints tested
- ✅ **Session Management**: Multi-session handling
- ✅ **RAG Functionality**: Document storage and retrieval
- ✅ **AI Integration**: Gemini API responses
- ✅ **Error Handling**: Graceful failure handling
- ✅ **Text Sanitization**: Clean output verification

### Manual Testing

```bash
# Health check
curl http://localhost:8000/api/health

# Create session and chat
curl -X POST http://localhost:8000/api/chat \
  -H "X-Session-ID: test-session" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, can you help me analyze flight data?"}'

# Check RAG stats
curl http://localhost:8000/api/rag/stats
```

## 🔧 Troubleshooting

### Common Issues

#### 1. API Key Not Found
**Error**: `GOOGLE_API_KEY not found in environment variables`

**Solution**: 
```bash
# Create .env file
echo "GOOGLE_API_KEY=your_api_key_here" > .env
```

#### 2. Import Errors
**Error**: `ModuleNotFoundError: No module named 'langchain_google_genai'`

**Solution**:
```bash
pip install -r requirements.txt
```

#### 3. Port Already in Use
**Error**: `Address already in use`

**Solution**:
```bash
# Kill existing process
lsof -ti:8000 | xargs kill -9

# Or use different port
export API_PORT=8001
python app.py
```

#### 4. Memory Issues
**Error**: High memory usage with many sessions

**Solution**:
```bash
# Trigger cleanup
curl -X POST http://localhost:8000/api/rag/cleanup

# Or clear specific session
curl -X POST http://localhost:8000/api/rag/collections/session_id/clear
```

### Debug Mode

Enable detailed logging:

```bash
export LOG_LEVEL=DEBUG
python app.py
```

### Performance Monitoring

Monitor system health:

```bash
# Check system stats
curl http://localhost:8000/api/rag/stats

# Check active sessions
curl http://localhost:8000/api/sessions

# Health check
curl http://localhost:8000/api/health
```

## 📊 Flight Data Structure

The API expects flight data in the following format:

```json
{
    "vehicle": "Copter|Plane|Rover|Tracker",
    "trajectories": {
        "GPS": {
            "trajectory": [[lon, lat, alt, time], ...],
            "timeTrajectory": {time: [lon, lat, alt, time], ...}
        }
    },
    "flightModeChanges": [[time, mode], ...],
    "events": [[time, event], ...],
    "mission": [...],
    "params": {...},
    "metadata": {
        "startTime": "2024-01-01T12:00:00"
    },
    "timeAttitude": {...},
    "fences": [...],
    "logType": "tlog|bin|dji"
}
```

## 🤖 AI Capabilities

The chat interface can respond to queries about:

- **GPS & Trajectory**: Flight path analysis, altitude profiles, speed analysis
- **Flight Modes**: Mode changes, transitions, and patterns
- **Events**: System events, errors, warnings, and milestones
- **Mission Data**: Waypoints, commands, mission progress, and completion
- **Parameters**: Vehicle configuration, settings, and calibration
- **Attitude Data**: Roll, pitch, yaw analysis and stability
- **Performance**: Flight efficiency, battery usage, and optimization
- **Troubleshooting**: Error diagnosis and recommendations

## 🔄 System Prompts

### Available Prompts

1. **ardupilot_analyst** (Default)
   - Specialized for ArduPilot data analysis
   - Focuses on flight modes, parameters, and system behavior

2. **uav_log_analysis**
   - General UAV log analysis
   - Covers multiple flight controller types

3. **flight_data_expert**
   - Expert-level flight performance analysis
   - Advanced insights and recommendations

## 🚀 Future Enhancements

### Planned Features
- **Multi-modal Support**: Image and audio analysis
- **Advanced RAG**: Hybrid search with vector embeddings
- **Real-time Streaming**: Live response streaming
- **Custom Tools**: User-defined analysis tools
- **Web Search Integration**: Real-time internet access
- **Multi-language Support**: Internationalization
- **Voice Interface**: Speech-to-text and text-to-speech

### Scalability Improvements
- **Database Integration**: PostgreSQL/MongoDB support
- **Redis Caching**: Session and response caching
- **Load Balancing**: Multi-instance deployment
- **Microservices**: Service decomposition
- **Container Orchestration**: Kubernetes deployment

## 📝 License

This project is part of the UAV Log Viewer system. See the main project repository for license information.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📞 Support

For issues and questions:
- Check the troubleshooting section
- Review the test files for usage examples
- Open an issue in the project repository

---

**Version**: 2.0.0  
**Last Updated**: 2024-01-01  
**Compatibility**: Python 3.8+, Flask 2.3+, Google Gemini API