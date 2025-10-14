# Flexible Chat System for UAV Log Viewer

## Overview

The backend has been enhanced with a flexible chat system that uses Google Gemini AI to provide dynamic, context-aware responses instead of preset answers. This allows for more natural and comprehensive analysis of UAV flight data.

## Key Features

### 🤖 AI-Powered Responses
- **Dynamic Responses**: Uses Google Gemini LLM to generate contextual answers
- **Context Awareness**: Incorporates flight data context into responses
- **RAG Integration**: Uses Retrieval Augmented Generation for better data analysis
- **Session-Based**: Each chat session has its own LLM agent and context

### 🔄 Flexible System Prompts
- **Multiple Prompts**: Switch between different AI personalities
- **ArduPilot Specialist**: Default prompt for ArduPilot data analysis
- **UAV Log Analyst**: Specialized for log file analysis
- **Flight Data Expert**: Expert-level flight performance analysis

### 📊 Enhanced Data Integration
- **Automatic RAG**: Flight data is automatically added to the RAG system
- **Context Building**: Session context is built from flight data summary
- **Smart Fallbacks**: Graceful degradation when AI services are unavailable

## API Endpoints

### Chat Endpoint
```
POST /api/chat
Headers: X-Session-ID: <session_id>
Body: {"message": "Your question here"}
```

### Flight Data Storage
```
POST /api/flight-data
Headers: X-Session-ID: <session_id>
Body: <flight_data_object>
```

### System Prompt Management
```
GET /api/prompts
# Returns available system prompts

POST /api/prompt/<session_id>
Body: {"prompt_name": "ardupilot_analyst"}
# Switch system prompt for a session
```

### Health Check
```
GET /api/health
# Returns system status including LLM agent availability
```

## System Prompts

### Available Prompts

1. **ardupilot_analyst** (Default)
   ```
   "You are a data analyst for ArduPilot data, answer all of the questions of the user. Refer the internet whenever required."
   ```

2. **uav_log_analysis**
   ```
   "You are a helpful AI assistant specialized in UAV log analysis and flight data interpretation. 
   You can help users understand flight logs, analyze telemetry data, and provide insights about UAV operations."
   ```

3. **flight_data_expert**
   ```
   "You are an expert in flight data analysis and UAV operations. 
   You can analyze telemetry data, identify patterns, troubleshoot issues, and provide detailed insights about flight performance."
   ```

## Usage Examples

### Basic Chat
```python
import requests

# Send a chat message
response = requests.post(
    "http://localhost:8000/api/chat",
    headers={"X-Session-ID": "your-session-id"},
    json={"message": "What can you tell me about this flight?"}
)

print(response.json()["message"])
```

### Switching System Prompts
```python
# Switch to a different AI personality
response = requests.post(
    "http://localhost:8000/api/prompt/your-session-id",
    json={"prompt_name": "flight_data_expert"}
)
```

### Storing Flight Data
```python
# Store flight data for analysis
flight_data = {
    "vehicle": "Quadcopter",
    "trajectories": {...},
    "flightModeChanges": [...],
    # ... other flight data
}

response = requests.post(
    "http://localhost:8000/api/flight-data",
    headers={"X-Session-ID": "your-session-id"},
    json=flight_data
)
```

## Architecture

### Components

1. **LangGraphReactAgent**: Main LLM agent with tool support
2. **SessionManager**: Manages sessions and LLM agents
3. **RAG System**: BM25-based retrieval for flight data
4. **Prompt Management**: Dynamic system prompt switching

### Data Flow

1. **Flight Data Upload** → Stored in session + Added to RAG
2. **User Question** → Enhanced with context → Sent to LLM
3. **LLM Response** → Context-aware answer → Returned to user

### Error Handling

- **Graceful Degradation**: Falls back to basic responses if LLM fails
- **Session Management**: Each session is isolated with its own agent
- **Context Preservation**: Flight data context is maintained across conversations

## Configuration

### Environment Variables

```bash
# Required
GOOGLE_API_KEY=your_gemini_api_key

# Optional
GOOGLE_MODEL_NAME=gemini-pro
SYSTEM_PROMPT=custom_prompt_here
```

### Dependencies

```bash
pip install -r requirements.txt
```

## Testing

### Run Tests
```bash
# Start the backend
python start_flexible_backend.py

# In another terminal, run tests
python test_flexible_chat.py
```

### Test Coverage

- ✅ Chat without flight data
- ✅ Chat with flight data context
- ✅ System prompt switching
- ✅ RAG integration
- ✅ Error handling and fallbacks

## Benefits

### For Users
- **Natural Conversations**: Ask questions in natural language
- **Comprehensive Analysis**: Get detailed insights about flight data
- **Flexible Interactions**: No need to use specific keywords
- **Context Awareness**: AI remembers previous conversation and data

### For Developers
- **Extensible**: Easy to add new system prompts
- **Maintainable**: Clean separation of concerns
- **Robust**: Comprehensive error handling
- **Scalable**: Session-based architecture supports multiple users

## Migration from Preset Responses

The old system used keyword matching and preset responses. The new system:

- **Replaces** hardcoded responses with AI-generated answers
- **Enhances** context awareness with flight data integration
- **Adds** RAG capabilities for better data analysis
- **Maintains** backward compatibility with existing API structure

## Future Enhancements

- **Web Search Integration**: Real-time internet access for current information
- **Advanced Analytics**: More sophisticated flight data analysis
- **Multi-language Support**: Support for different languages
- **Custom Prompts**: User-defined system prompts
- **Voice Interface**: Speech-to-text and text-to-speech capabilities
