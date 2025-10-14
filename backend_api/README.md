# UAV Log Viewer Backend API

A Flask-based REST API that provides session-based chat functionality for the UAV Log Viewer frontend. The API can handle multiple concurrent sessions and provides contextual responses based on uploaded flight data.

## Features

- **Multi-Session Support**: Handle multiple users simultaneously with unique session IDs
- **Flight Data Integration**: Store and analyze flight data from uploaded log files
- **Contextual Chat**: Provide intelligent responses based on available flight data
- **Data Summary**: Extract and summarize key flight information
- **CORS Enabled**: Ready for frontend integration

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Running the API

```bash
python app.py
```

The API will start on `http://localhost:8000`

## API Endpoints

### 1. Chat Endpoint
**POST** `/api/chat`

Send messages to the chat interface.

**Headers:**
- `X-Session-ID`: Unique session identifier
- `Content-Type`: application/json

**Request Body:**
```json
{
    "message": "What flight modes were used?",
    "sessionId": "session_xxx",
    "timestamp": 1234567890
}
```

**Response:**
```json
{
    "message": "I can see your vehicle used 3 different flight modes: STABILIZE, AUTO, RTL...",
    "session_id": "session_xxx",
    "timestamp": "2024-01-01T12:00:00"
}
```

### 2. Flight Data Storage
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
    "message": "Flight data stored successfully"
}
```

### 3. Session Information
**GET** `/api/session/{session_id}`

Get information about a specific session.

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

### 4. List All Sessions
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

### 5. Health Check
**GET** `/api/health`

Check API health and status.

**Response:**
```json
{
    "status": "healthy",
    "timestamp": "2024-01-01T12:00:00",
    "active_sessions": 2,
    "cached_flight_data": 2
}
```

## Flight Data Structure

The API expects flight data in the following format (matching the frontend's global state):

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
    "fences": [...]
}
```

## Chat Capabilities

The chat interface can respond to queries about:

- **GPS & Trajectory**: Flight path, altitude, speed analysis
- **Flight Modes**: Mode changes and transitions  
- **Events**: System events, errors, and milestones
- **Mission Data**: Waypoints, commands, and mission progress
- **Parameters**: Vehicle configuration and settings
- **Attitude Data**: Roll, pitch, yaw data and analysis
- **General Help**: Overview of available data and capabilities

## Session Management

- Sessions are created automatically when first accessed
- Each session maintains its own chat history and flight data
- Sessions persist until the server is restarted (in-memory storage)
- Session IDs should be unique UUIDs or timestamp-based identifiers

## Integration with Frontend

The frontend chat window should:

1. Generate a unique session ID when the chat is first opened
2. Send the session ID in the `X-Session-ID` header with all requests
3. Call `/api/flight-data` when a log file is processed
4. Use `/api/chat` for all user messages
5. Handle responses and display them in the chat interface

## Error Handling

The API returns appropriate HTTP status codes:
- `200`: Success
- `400`: Bad Request (missing parameters)
- `404`: Session not found
- `500`: Internal server error

All error responses include a JSON object with an `error` field describing the issue.
