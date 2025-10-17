# UAV Log Viewer - Backend API

Agentic chatbot backend using LangGraph React agents and Google Gemini API for intelligent flight data analysis.

## Features

- 🤖 **Agentic Analysis**: LangGraph-based React agent that reasons about flight data
- 💬 **Session-based Chat**: Each session maintains independent conversation and flight data
- 📊 **Telemetry Retrieval**: Dynamic extraction of GPS, battery, altitude, attitude data
- 🔍 **Anomaly Detection**: Intelligent detection of GPS issues, battery problems, and flight anomalies
- 🧠 **Google Gemini Integration**: Powered by Gemini 1.5 for natural language understanding
- 🗄️ **Qdrant Support**: Optional vector database for semantic search (documentation)

## Quick Start

### 1. Prerequisites

- Python 3.10+ (conda environment recommended)
- Google Gemini API key
- Qdrant (optional, for documentation search)

### 2. Setup

```bash
# Navigate to backend directory
cd backend_api

# Create .env file
cp .env.example .env

# Edit .env and add your Google API key
# GOOGLE_API_KEY=your_actual_api_key_here

# Install dependencies (using conda arena env)
conda activate arena
pip install -r requirements.txt
```

### 3. Configure Qdrant Cloud (Optional)

```bash
# Add to your .env file:
QDRANT_URL=https://your-cluster-id.eu-central-1.aws.cloud.qdrant.io
QDRANT_API_KEY=your_qdrant_api_key_here

# Or skip this - the backend will work without Qdrant
```

### 4. Run the Backend

```bash
# Using Python
python app.py

# Or using Flask directly
flask run --host=0.0.0.0 --port=8000
```

The API will start on `http://localhost:8000`

## API Endpoints

### Health Check
```
GET /api/health
```

### Upload Flight Data
```
POST /api/flight-data
Headers: X-Session-ID: <session_id>
Body: JSON flight data from frontend
```

### Chat
```
POST /api/chat
Headers: X-Session-ID: <session_id>
Body: {
  "message": "What was the maximum altitude?",
  "sessionId": "<session_id>",
  "timestamp": 1234567890
}
```

### Get Session Summary
```
GET /api/session/<session_id>/summary
```

### Get Telemetry Data
```
GET /api/telemetry/<session_id>/<parameter>
Parameters: GPS, BATTERY, ALTITUDE, ATTITUDE, EVENTS
```

### Get Anomalies
```
GET /api/anomalies/<session_id>
```

## Architecture

### Agent Flow

The backend uses a simple React-style agent:

```
1. THINK: Analyze user question, decide what data is needed
2. ACT: Retrieve telemetry data, detect anomalies, etc.
3. OBSERVE: Process results
4. REPEAT: Continue if more information needed (max 3 iterations)
5. RESPOND: Generate natural language answer using Gemini
```

### Services

- **SessionManager**: Manages user sessions and flight data
- **TelemetryService**: Extracts and analyzes flight parameters
- **GeminiService**: Interfaces with Google Gemini API
- **QdrantService**: Vector database for documentation (optional)
- **FlightAnalysisAgent**: LangGraph agent orchestrating analysis

## Example Questions

Users can ask questions like:

- "What was the highest altitude reached during the flight?"
- "When did the GPS signal first get lost?"
- "What was the maximum battery temperature?"
- "Are there any anomalies in this flight?"
- "Can you spot any issues in the GPS data?"
- "How long was the total flight time?"

The agent will:
1. Determine what data is needed
2. Retrieve relevant telemetry
3. Detect anomalies if needed
4. Provide a comprehensive, data-driven answer

## Configuration

Edit `.env` file:

```bash
# Required
GOOGLE_API_KEY=your_gemini_api_key

# Optional
QDRANT_URL=http://localhost:6333
FLASK_PORT=8000
MAX_AGENT_ITERATIONS=5
```

## Development

### Project Structure

```
backend_api/
├── app.py                 # Flask application
├── config.py              # Configuration
├── models.py              # Data models
├── session_manager.py     # Session management
├── telemetry_service.py   # Telemetry extraction
├── gemini_service.py      # Gemini API integration
├── qdrant_service.py      # Vector database
├── agent.py               # LangGraph agent
└── requirements.txt       # Dependencies
```

### Adding New Features

**New telemetry parameter:**
1. Add extraction logic in `telemetry_service.py`
2. Update `_create_flight_summary()` to detect it
3. Add action in `agent.py` if needed

**New agent action:**
1. Add condition in `agent._think_node()`
2. Implement in `agent._act_node()`

## Troubleshooting

### "GOOGLE_API_KEY is required"
- Make sure you created a `.env` file with your API key

### "Could not connect to Qdrant"
- This is a warning, not an error. The backend works without Qdrant.
- If you want vector search, start Qdrant with Docker

### Agent not providing good answers
- Increase `MAX_AGENT_ITERATIONS` in `.env`
- Check that flight data was uploaded successfully
- Review logs for errors

## License

Same as UAVLogViewer main project

