# Telemetry Data Documentation
## UAV Log Viewer Backend API

### Overview
This document provides comprehensive documentation for the telemetry data system in the UAV Log Viewer Backend API. The system processes, analyzes, and provides AI-powered insights on UAV flight data from various sources including ArduPilot logs, MAVLink data, and DJI logs.

---

## Table of Contents

1. [Data Architecture](#1-data-architecture)
2. [Flight Data Schema](#2-flight-data-schema)
3. [Telemetry Parameters](#3-telemetry-parameters)
4. [Data Processing Pipeline](#4-data-processing-pipeline)
5. [Anomaly Detection System](#5-anomaly-detection-system)
6. [Statistical Analysis](#6-statistical-analysis)
7. [ArduPilot Integration](#7-ardupilot-integration)
8. [API Endpoints](#8-api-endpoints)
9. [Data Quality & Validation](#9-data-quality--validation)
10. [Performance Considerations](#10-performance-considerations)

---

## 1. Data Architecture

### 1.1 System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Telemetry Data Flow                      │
├─────────────────────────────────────────────────────────────┤
│  Frontend Upload → Session Manager → Data Normalization    │
│                           ↓                                │
│  Telemetry Retriever → Anomaly Detector → Statistical      │
│                           ↓                                │
│  RAG System → LLM Agent → AI Analysis → Response           │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Data Storage Layers

- **Session Cache**: In-memory storage for active flight data
- **RAG System**: Qdrant vector database for document storage
- **Telemetry Cache**: Dynamic parameter extraction and caching
- **Anomaly Cache**: Statistical analysis and pattern storage

### 1.3 Data Flow Architecture

1. **Ingestion**: Flight data uploaded via REST API
2. **Normalization**: Data standardized to backend schema
3. **Processing**: Parameter extraction and time-series analysis
4. **Analysis**: Statistical analysis and anomaly detection
5. **Storage**: RAG document creation and vector storage
6. **Query**: Dynamic parameter queries and AI analysis

---

## 2. Flight Data Schema

### 2.1 Core Flight Data Structure

```json
{
  "vehicle": "Copter|Plane|Rover|Tracker",
  "logType": "tlog|bin|dji",
  "metadata": {
    "startTime": "2024-01-01T12:00:00Z",
    "duration": 3600,
    "version": "1.0"
  },
  "trajectories": {
    "GPS": {
      "trajectory": [[lon, lat, alt, timestamp], ...],
      "timeTrajectory": {timestamp: [lon, lat, alt, timestamp], ...}
    }
  },
  "gps_metadata": {
    "status_changes": [
      {
        "timestamp": 1234567890,
        "status": "GPS_OK|NO_GPS|NO_FIX",
        "fix_type": "NO_FIX|2D|3D|DGPS|RTK_FLOAT|RTK_FIXED"
      }
    ],
    "satellite_counts": [8, 9, 10, 8, 7, ...],
    "signal_quality": [
      {
        "timestamp": 1234567890,
        "hdop": 1.2,
        "vdop": 1.8
      }
    ],
    "accuracy_metrics": [
      {
        "timestamp": 1234567890,
        "hacc": 2.5,
        "vacc": 3.1,
        "sacc": 0.8
      }
    ]
  },
  "attitude_series": [
    {
      "timestamp": 1234567890,
      "roll": 0.5,
      "pitch": -1.2,
      "yaw": 45.0
    }
  ],
  "battery_series": [
    {
      "timestamp": 1234567890,
      "voltage": 12.6,
      "current": 15.2,
      "remaining": 85,
      "temperature": 25.0
    }
  ],
  "rc_inputs": [
    {
      "timestamp": 1234567890,
      "signal_strength": 95,
      "signal_lost": false
    }
  ],
  "flightModeChanges": [
    [1234567890, "STABILIZE"],
    [1234567891, "AUTO"],
    [1234567892, "RTL"]
  ],
  "events": [
    {
      "timestamp": 1234567890,
      "type": "ARMED",
      "message": "Vehicle armed",
      "severity": "info"
    }
  ],
  "mission": [
    {
      "command": "MAV_CMD_NAV_WAYPOINT",
      "param1": 0,
      "param2": 0,
      "param3": 0,
      "param4": 0,
      "x": -122.4194,
      "y": 37.7749,
      "z": 100
    }
  ],
  "params": {
    "PARAM_NAME": "value",
    "BAT_VOLT_MULT": 10.1,
    "GPS_TYPE": 1
  },
  "fences": [
    {
      "type": "polygon",
      "points": [[lon, lat], ...]
    }
  ]
}
```

### 2.2 Data Normalization

The system includes comprehensive data normalization to handle various input formats:

```python
def _normalize_flight_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalizes incoming flight data to backend-friendly schema:
    - params: ensure dict of {name: value}
    - events: ensure list of dicts with at least {timestamp, type, message}
    - attitude_series: derive from timeAttitude if present
    - rc_inputs: pass-through if present, else omit
    """
```

**Normalization Rules:**
- **Parameters**: Convert list format `[timestamp, name, value]` to dict `{name: value}`
- **Events**: Standardize to `{timestamp, type, message, severity}` format
- **Attitude**: Extract from `timeAttitude` map to `attitude_series` list
- **Trajectories**: Ensure consistent `[lon, lat, alt, timestamp]` format

---

## 3. Telemetry Parameters

### 3.1 Parameter Categories

#### 3.1.1 Navigation Parameters
```python
'navigation': [
    'gps_lat', 'gps_lon', 'gps_alt', 
    'gps_accuracy', 'heading', 'ground_speed'
]
```

**GPS Position Data:**
- **Latitude/Longitude**: Decimal degrees (WGS84)
- **Altitude**: Meters above sea level
- **Accuracy**: Horizontal/Vertical accuracy in meters
- **Satellite Count**: Number of satellites in view
- **Fix Type**: GPS fix quality (NO_FIX, 2D, 3D, DGPS, RTK)

**Signal Quality:**
- **HDop**: Horizontal Dilution of Precision (lower is better)
- **VDop**: Vertical Dilution of Precision (lower is better)
- **Status**: GPS signal status and health

#### 3.1.2 Attitude Parameters
```python
'attitude': [
    'roll', 'pitch', 'yaw', 
    'roll_rate', 'pitch_rate', 'yaw_rate'
]
```

**Attitude Data:**
- **Roll**: Rotation around longitudinal axis (degrees)
- **Pitch**: Rotation around lateral axis (degrees)
- **Yaw**: Rotation around vertical axis (degrees)
- **Rates**: Angular velocities (degrees/second)

#### 3.1.3 Power Parameters
```python
'power': [
    'battery_voltage', 'battery_current', 
    'battery_remaining', 'power_consumption'
]
```

**Battery Data:**
- **Voltage**: Battery voltage in volts
- **Current**: Current draw in amperes
- **Remaining**: Battery percentage remaining
- **Temperature**: Battery temperature in Celsius

#### 3.1.4 Sensor Parameters
```python
'sensors': [
    'imu_accel_x', 'imu_accel_y', 'imu_accel_z',
    'imu_gyro_x', 'imu_gyro_y', 'imu_gyro_z'
]
```

**IMU Data:**
- **Accelerometer**: Linear acceleration (m/s²)
- **Gyroscope**: Angular velocity (rad/s)
- **Magnetometer**: Magnetic field strength (gauss)

#### 3.1.5 Control Parameters
```python
'control': [
    'rc_signal_strength', 'rc_signal_lost',
    'flight_mode', 'armed_status'
]
```

**RC Input Data:**
- **Signal Strength**: RSSI percentage (0-100%)
- **Signal Lost**: Boolean flag for signal loss
- **Channel Data**: PWM values for control channels

### 3.2 Parameter Extraction

The system dynamically extracts parameters from flight data:

```python
def _extract_parameter_data(self, flight_data: Dict[str, Any], parameter: str) -> List[Dict[str, Any]]:
    """
    Comprehensive parameter extraction with support for:
    - GPS trajectory data
    - Attitude series
    - Battery monitoring
    - RC input data
    - Flight mode changes
    - Event data
    - Mission data
    """
```

**Extraction Methods:**
- **Direct Access**: Parameters stored in standard fields
- **Derived Calculation**: Computed from available data
- **Pattern Matching**: Search across multiple data sources
- **Type Conversion**: Ensure proper data types

---

## 4. Data Processing Pipeline

### 4.1 Processing Stages

#### Stage 1: Data Ingestion
```python
def store_flight_data(self, session_id: str, flight_data: Dict[str, Any]):
    """
    1. Validate input data structure
    2. Normalize data format
    3. Store in session cache
    4. Sync to telemetry retriever
    5. Update session context
    """
```

#### Stage 2: Parameter Extraction
```python
def _extract_parameter_data(self, flight_data: Dict[str, Any], parameter: str):
    """
    1. Identify parameter category
    2. Extract from appropriate data source
    3. Apply data transformations
    4. Validate extracted data
    5. Return structured results
    """
```

#### Stage 3: Time Series Analysis
```python
def _extract_time_series_data(self, flight_data: Dict[str, Any]):
    """
    1. Extract temporal data points
    2. Sort by timestamp
    3. Handle missing values
    4. Calculate derived metrics
    5. Store in time series format
    """
```

#### Stage 4: Statistical Analysis
```python
def _calculate_statistical_summary(self, time_series: Dict[str, List[Tuple[float, Any]]]):
    """
    1. Calculate basic statistics (min, max, mean, std)
    2. Determine data trends
    3. Identify outliers
    4. Compute correlation coefficients
    5. Generate quality metrics
    """
```

### 4.2 Data Transformation

**Time Series Conversion:**
```python
# Raw data: [timestamp, value]
# Processed: [(timestamp, value), ...]
time_series = [(point[0], point[1]) for point in raw_data]
```

**Statistical Calculations:**
```python
statistical_summary = {
    'count': len(values),
    'min': min(values),
    'max': max(values),
    'mean': statistics.mean(values),
    'std_dev': statistics.stdev(values),
    'trend': 'increasing|decreasing|stable'
}
```

---

## 5. Anomaly Detection System

### 5.1 Anomaly Types

#### 5.1.1 Sudden Changes
```python
'sudden_changes': [
    'altitude', 'velocity', 'battery_voltage', 'gps_accuracy'
]
```

**Detection Method:**
- **Threshold**: 3-sigma rule (3 × standard deviation)
- **Time Window**: Consecutive data points
- **Severity**: Based on change magnitude

```python
def _detect_sudden_changes(self, data_points: List[Tuple[float, Any]], stats: Dict[str, float]):
    change_threshold = stats['std_dev'] * 3  # 3-sigma rule
    for i in range(1, len(data_points)):
        change = abs(curr_value - prev_value)
        if change > change_threshold:
            # Anomaly detected
```

#### 5.1.2 Threshold Violations
```python
'threshold_violations': [
    'battery_voltage', 'temperature', 'altitude', 'speed'
]
```

**Parameter Thresholds:**
```python
thresholds = {
    'battery_voltage': {'min': 10.0, 'max': 15.0},
    'gps_alt': {'min': -100.0, 'max': 1000.0},
    'gps_accuracy': {'max': 5.0},
    'temperature': {'min': -20.0, 'max': 60.0}
}
```

#### 5.1.3 GPS-Specific Anomalies

**GPS Signal Loss:**
```python
def _detect_gps_anomalies(self, time_series: Dict[str, List[Tuple[float, Any]]]):
    # GPS status changes
    if status in ['NO_GPS', 'NO_FIX']:
        anomalies.append({
            'type': 'GPS_SIGNAL_LOSS',
            'severity': 'high',
            'timestamp': timestamp,
            'description': f'GPS signal lost: {status}'
        })
```

**Satellite Count Drops:**
```python
# Detect rapid satellite count drops
if prev_count is not None and prev_count - count > 3:
    anomalies.append({
        'type': 'SATELLITE_COUNT_DROP',
        'severity': 'high',
        'description': f'Rapid satellite count drop: {prev_count} to {count}'
    })
```

**GPS Accuracy Degradation:**
```python
# Poor GPS accuracy
if hacc > 5.0:  # > 5 meters horizontal accuracy
    severity = 'critical' if hacc > 20.0 else 'medium'
    anomalies.append({
        'type': 'GPS_ACCURACY_DEGRADATION',
        'severity': severity,
        'description': f'Poor GPS accuracy: {hacc:.1f}m horizontal'
    })
```

#### 5.1.4 Battery Anomalies

**Critical Low Voltage:**
```python
if voltage < 10.5:  # Critical low voltage
    anomalies.append({
        'type': 'BATTERY_CRITICAL_LOW',
        'severity': 'critical',
        'description': f'Critical battery voltage: {voltage:.1f}V'
    })
```

**Temperature Issues:**
```python
if temp > 60.0:  # High temperature
    anomalies.append({
        'type': 'HIGH_TEMPERATURE',
        'severity': 'high',
        'description': f'High temperature: {temp:.1f}°C'
    })
```

#### 5.1.5 RC Signal Anomalies

**Signal Loss:**
```python
if signal_lost == 1:  # Signal lost
    anomalies.append({
        'type': 'RC_SIGNAL_LOSS',
        'severity': 'critical',
        'description': 'RC signal lost - vehicle may enter failsafe mode'
    })
```

### 5.2 Anomaly Severity Levels

- **Critical**: Immediate safety concern (RC signal loss, critical battery)
- **High**: Significant issue requiring attention (GPS loss, high temperature)
- **Medium**: Moderate concern (accuracy degradation, low battery)
- **Low**: Minor issue or warning (weak signal, elevated temperature)

### 5.3 Anomaly Context

Each anomaly includes contextual information:
```python
@dataclass
class AnomalyContext:
    parameter: str
    value: Any
    timestamp: float
    expected_range: Optional[Tuple[float, float]] = None
    historical_avg: Optional[float] = None
    trend: Optional[str] = None
    severity: str = 'low'
    description: str = ""
    related_parameters: List[str] = None
```

---

## 6. Statistical Analysis

### 6.1 Statistical Metrics

#### 6.1.1 Basic Statistics
```python
statistical_summary = {
    'count': len(values),           # Number of data points
    'min': min(values),             # Minimum value
    'max': max(values),             # Maximum value
    'mean': statistics.mean(values), # Average value
    'median': statistics.median(values), # Median value
    'std_dev': statistics.stdev(values), # Standard deviation
    'range': max(values) - min(values),  # Value range
    'first_value': values[0],       # First data point
    'last_value': values[-1],       # Last data point
    'time_span': max(timestamps) - min(timestamps) # Time duration
}
```

#### 6.1.2 Trend Analysis
```python
def calculate_trend(self, timestamps: List[float], values: List[float]):
    """
    Calculate trend using linear regression:
    - slope > 0.01: 'increasing'
    - slope < -0.01: 'decreasing'
    - else: 'stable'
    """
    x = np.array(timestamps)
    y = np.array(values)
    slope = np.polyfit(x, y, 1)[0]
    
    if slope > 0.01:
        return 'increasing'
    elif slope < -0.01:
        return 'decreasing'
    else:
        return 'stable'
```

#### 6.1.3 Variance Analysis
```python
def _detect_variance_anomalies(self, data_points: List[Tuple[float, Any]], stats: Dict[str, float]):
    """
    Detect unusual variance using coefficient of variation:
    - CV > 0.5 (50%): High variance detected
    """
    coefficient_of_variation = stats['std_dev'] / abs(stats['mean'])
    
    if coefficient_of_variation > 0.5:
        return {
            'type': 'high_variance',
            'severity': 'medium',
            'coefficient_of_variation': coefficient_of_variation,
            'description': f'High variance detected (CV: {coefficient_of_variation:.2f})'
        }
```

### 6.2 Flight Phase Detection

#### 6.2.1 Phase Identification
```python
def _identify_flight_phases(self, time_series: Dict[str, List[Tuple[float, Any]]]):
    """
    Identify flight phases based on altitude changes:
    - Takeoff: Rapid altitude increase
    - Cruise: Stable altitude
    - Landing: Rapid altitude decrease
    """
    if 'gps_alt' in time_series:
        altitudes = [value for _, value in alt_data]
        min_alt = min(altitudes)
        max_alt = max(altitudes)
        alt_range = max_alt - min_alt
        
        # Takeoff phase (rapid altitude increase)
        takeoff_threshold = min_alt + alt_range * 0.1
        takeoff_points = [(t, a) for t, a in zip(timestamps, altitudes) if a > takeoff_threshold]
        
        # Cruise phase (stable altitude)
        cruise_threshold = min_alt + alt_range * 0.3
        cruise_points = [(t, a) for t, a in zip(timestamps, altitudes) 
                        if cruise_threshold <= a <= max_alt - alt_range * 0.1]
```

### 6.3 Quality Metrics

#### 6.3.1 Data Completeness
```python
quality_metrics = {
    'total_parameters': len(time_series),
    'parameters_with_data': len([p for p in time_series.values() if p]),
    'data_completeness': total_possible_points / (len(time_series) * 100),
    'temporal_coverage': max(timestamps) - min(timestamps),
    'parameter_correlation': correlation_matrix
}
```

---

## 7. ArduPilot Integration

### 7.1 Message Types

#### 7.1.1 GPS Messages
```python
"GPS": {
    "description": "GPS position and velocity data",
    "fields": {
        "Status": {"description": "GPS fix status", "units": "enum"},
        "NSats": {"description": "Number of satellites", "units": "count"},
        "HDop": {"description": "Horizontal dilution of precision", "units": "ratio"},
        "VDop": {"description": "Vertical dilution of precision", "units": "ratio"},
        "Lat": {"description": "Latitude", "units": "degrees"},
        "Lng": {"description": "Longitude", "units": "degrees"},
        "Alt": {"description": "Altitude", "units": "meters"},
        "Spd": {"description": "Ground speed", "units": "m/s"},
        "GCrs": {"description": "Ground course", "units": "degrees"}
    }
}
```

#### 7.1.2 Battery Messages
```python
"BAT": {
    "description": "Battery voltage and current",
    "fields": {
        "Volt": {"description": "Battery voltage", "units": "volts"},
        "Curr": {"description": "Battery current", "units": "amperes"},
        "CurrTot": {"description": "Total current consumed", "units": "amperes"},
        "Res": {"description": "Battery resistance", "units": "ohms"}
    }
}
```

#### 7.1.3 Attitude Messages
```python
"ATT": {
    "description": "Attitude data - roll, pitch, yaw angles",
    "fields": {
        "Roll": {"description": "Roll angle", "units": "degrees"},
        "Pitch": {"description": "Pitch angle", "units": "degrees"},
        "Yaw": {"description": "Yaw angle", "units": "degrees"},
        "DesRoll": {"description": "Desired roll angle", "units": "degrees"},
        "DesPitch": {"description": "Desired pitch angle", "units": "degrees"},
        "DesYaw": {"description": "Desired yaw angle", "units": "degrees"}
    }
}
```

#### 7.1.4 Mode Messages
```python
"MODE": {
    "description": "Flight mode changes",
    "fields": {
        "Mode": {"description": "Flight mode", "units": "enum"},
        "Rsn": {"description": "Reason for mode change", "units": "enum"}
    }
}
```

#### 7.1.5 Error Messages
```python
"ERR": {
    "description": "Error and warning messages",
    "fields": {
        "Subsys": {"description": "Subsystem", "units": "enum"},
        "ECode": {"description": "Error code", "units": "enum"}
    }
}
```

#### 7.1.6 RC Input Messages
```python
"RCIN": {
    "description": "RC input channels",
    "fields": {
        "C1": {"description": "Channel 1", "units": "PWM"},
        "C2": {"description": "Channel 2", "units": "PWM"},
        "C3": {"description": "Channel 3", "units": "PWM"},
        "C4": {"description": "Channel 4", "units": "PWM"},
        "C5": {"description": "Channel 5", "units": "PWM"},
        "C6": {"description": "Channel 6", "units": "PWM"},
        "C7": {"description": "Channel 7", "units": "PWM"},
        "C8": {"description": "Channel 8", "units": "PWM"}
    }
}
```

### 7.2 Documentation Integration

The system integrates with ArduPilot documentation:

```python
def get_parameter_documentation(self, parameter: str) -> Dict[str, Any]:
    """
    Retrieves ArduPilot documentation for parameters:
    1. Try exact match
    2. Try case-insensitive match
    3. Try partial match
    4. Return default documentation
    """
```

**Documentation Sources:**
- **Primary**: ArduPilot.org log messages documentation
- **Fallback**: Built-in parameter definitions
- **Cache**: 1-hour cache duration for performance

---

## 8. API Endpoints

### 8.1 Telemetry Query Endpoint

#### 8.1.1 Query Specific Parameters
```http
POST /api/telemetry/{session_id}/query
Content-Type: application/json
X-Session-ID: {session_id}

{
    "parameter": "GPS",
    "time_range": [1234567890, 1234567899],
    "aggregation": "raw"
}
```

**Response:**
```json
{
    "parameter": "GPS",
    "documentation": {
        "type": "GPS",
        "description": "GPS position and velocity data",
        "fields": {...}
    },
    "field_documentation": {
        "lat": {"description": "Latitude", "units": "degrees"},
        "lon": {"description": "Longitude", "units": "degrees"}
    },
    "data": [
        {
            "timestamp": 1234567890,
            "lat": 37.7749,
            "lon": -122.4194,
            "alt": 100.0,
            "type": "gps_position"
        }
    ],
    "data_points": 150,
    "ardupilot_reference": "https://ardupilot.org/plane/docs/logmessages.html#gps"
}
```

#### 8.1.2 Get Telemetry Summary
```http
GET /api/telemetry/{session_id}/summary
```

**Response:**
```json
{
    "session_id": "session_123",
    "available_parameters": [
        "GPS", "GPS_POSITION", "BATTERY", "ATTITUDE", 
        "MODE", "EVENTS", "PARAMETERS"
    ],
    "data_sources": [
        {
            "type": "trajectories",
            "count": 1,
            "description": "GPS trajectory data"
        },
        {
            "type": "events",
            "count": 45,
            "description": "Flight events and messages"
        }
    ]
}
```

### 8.2 Anomaly Analysis Endpoint

#### 8.2.1 Analyze Flight Anomalies
```http
POST /api/anomaly/{session_id}/analyze
Content-Type: application/json

{
    "question": "Are there any GPS issues in this flight?"
}
```

**Response:**
```json
{
    "session_id": "session_123",
    "telemetry_summary": {
        "flight_duration": 1800.0,
        "total_data_points": 5000,
        "parameters_analyzed": ["gps_lat", "gps_lon", "gps_alt", "battery_voltage"],
        "anomaly_indicators_count": 3,
        "flight_phases_count": 3
    },
    "anomaly_indicators": [
        {
            "type": "GPS_SIGNAL_LOSS",
            "severity": "high",
            "timestamp": 1234567890,
            "description": "GPS signal lost: NO_FIX",
            "confidence": 0.9
        }
    ],
    "flight_phases": [
        {
            "phase": "takeoff",
            "start_time": 0,
            "end_time": 120,
            "altitude_range": [0, 50],
            "description": "Takeoff phase detected"
        }
    ],
    "statistical_summary": {
        "gps_alt": {
            "min": 0.0,
            "max": 150.5,
            "mean": 75.2,
            "std_dev": 45.1,
            "trend": "increasing"
        }
    }
}
```

### 8.3 Data Completeness Endpoint

#### 8.3.1 Get Data Completeness Report
```http
GET /api/data-completeness/{session_id}
```

**Response:**
```json
{
    "session_id": "session_123",
    "total_parameters": 25,
    "data_sources": {
        "trajectories": {
            "count": 1,
            "total_points": 1500
        },
        "events": {
            "count": 45
        },
        "flight_modes": {
            "count": 5
        },
        "parameters": {
            "count": 120
        }
    },
    "parameter_categories": {
        "gps": ["GPS", "GPS_POSITION", "GPS_COORDINATES"],
        "battery": ["BATTERY", "BATTERY_VOLTAGE"],
        "rc_control": ["RC", "RC_INPUT", "RSSI"],
        "flight_modes": ["MODE", "FLIGHT_MODE"],
        "events": ["EVENTS", "ALL_EVENTS"],
        "parameters": ["PARAMETERS", "ALL_PARAMETERS"],
        "mission": ["MISSION", "MISSION_DATA"]
    },
    "data_quality_indicators": {
        "has_trajectory_data": true,
        "has_gps_metadata": true,
        "has_flight_modes": true,
        "has_events": true,
        "has_parameters": true,
        "has_mission_data": false,
        "has_rc_data": true
    }
}
```

---

## 9. Data Quality & Validation

### 9.1 Input Validation

#### 9.1.1 Data Structure Validation
```python
def validate_flight_data(self, flight_data: Dict[str, Any]) -> bool:
    """
    Validates flight data structure:
    1. Check required fields
    2. Validate data types
    3. Check value ranges
    4. Verify timestamp consistency
    """
    required_fields = ['vehicle', 'trajectories']
    
    for field in required_fields:
        if field not in flight_data:
            return False
    
    # Validate trajectory format
    if 'trajectories' in flight_data:
        for traj_name, traj_data in flight_data['trajectories'].items():
            if 'trajectory' not in traj_data:
                return False
            
            trajectory = traj_data['trajectory']
            for point in trajectory:
                if not isinstance(point, (list, tuple)) or len(point) < 3:
                    return False
```

#### 9.1.2 Data Type Validation
```python
def validate_data_types(self, data: Any, expected_type: type) -> bool:
    """
    Validates data types for telemetry parameters:
    - Numeric values: int, float
    - Timestamps: numeric (Unix timestamp)
    - Strings: str
    - Booleans: bool
    """
    if expected_type == (int, float):
        return isinstance(data, (int, float)) and not isinstance(data, bool)
    return isinstance(data, expected_type)
```

### 9.2 Data Sanitization

#### 9.2.1 Text Sanitization
```python
def sanitize_text(text: str) -> str:
    """
    Sanitizes text data:
    1. Decode HTML entities
    2. Remove markdown formatting
    3. Remove URLs
    4. Normalize whitespace
    5. Remove special Unicode characters
    """
    # Decode HTML entities
    text = html.unescape(text)
    
    # Remove markdown formatting
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Bold
    text = re.sub(r'\*(.*?)\*', r'\1', text)      # Italic
    text = re.sub(r'`(.*?)`', r'\1', text)        # Code
    
    # Remove URLs
    text = re.sub(r'https?://[^\s]+', '', text)
    
    # Normalize whitespace
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    
    return text.strip()
```

#### 9.2.2 Numeric Data Validation
```python
def validate_numeric_data(self, value: Any, min_val: float = None, max_val: float = None) -> bool:
    """
    Validates numeric data with range checking:
    - Check if value is numeric
    - Check if within expected range
    - Handle NaN and infinity values
    """
    if not isinstance(value, (int, float)):
        return False
    
    if math.isnan(value) or math.isinf(value):
        return False
    
    if min_val is not None and value < min_val:
        return False
    
    if max_val is not None and value > max_val:
        return False
    
    return True
```

### 9.3 Error Handling

#### 9.3.1 Graceful Degradation
```python
def extract_parameter_with_fallback(self, flight_data: Dict[str, Any], parameter: str):
    """
    Extract parameter with graceful fallback:
    1. Try primary extraction method
    2. Try alternative data sources
    3. Return partial data if available
    4. Log warnings for missing data
    """
    try:
        # Primary extraction
        return self._extract_parameter_data(flight_data, parameter)
    except Exception as e:
        logger.warning(f"Primary extraction failed for {parameter}: {e}")
        
        try:
            # Fallback extraction
            return self._extract_parameter_fallback(flight_data, parameter)
        except Exception as e:
            logger.error(f"Fallback extraction failed for {parameter}: {e}")
            return []
```

#### 9.3.2 Data Completeness Reporting
```python
def calculate_data_completeness(self, flight_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate data completeness metrics:
    - Parameter coverage
    - Temporal coverage
    - Data quality scores
    - Missing data identification
    """
    completeness = {
        'total_parameters': 0,
        'available_parameters': 0,
        'data_coverage': 0.0,
        'temporal_coverage': 0.0,
        'quality_score': 0.0
    }
    
    # Calculate parameter coverage
    expected_params = ['GPS', 'BATTERY', 'ATTITUDE', 'MODE', 'EVENTS']
    available_params = self._get_available_parameters(flight_data)
    
    completeness['total_parameters'] = len(expected_params)
    completeness['available_parameters'] = len(available_params)
    completeness['data_coverage'] = len(available_params) / len(expected_params)
    
    return completeness
```

---

## 10. Performance Considerations

### 10.1 Memory Management

#### 10.1.1 Data Caching Strategy
```python
class TelemetryCache:
    """
    Memory-efficient caching for telemetry data:
    - LRU cache for frequently accessed parameters
    - Lazy loading for large datasets
    - Memory limits and cleanup
    """
    def __init__(self, max_size: int = 1000):
        self.cache = {}
        self.max_size = max_size
        self.access_times = {}
    
    def get(self, key: str) -> Any:
        if key in self.cache:
            self.access_times[key] = time.time()
            return self.cache[key]
        return None
    
    def put(self, key: str, value: Any):
        if len(self.cache) >= self.max_size:
            self._evict_oldest()
        
        self.cache[key] = value
        self.access_times[key] = time.time()
```

#### 10.1.2 Large Dataset Handling
```python
def process_large_dataset(self, flight_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process large datasets efficiently:
    1. Stream processing for large trajectories
    2. Chunked processing for memory efficiency
    3. Progress tracking for long operations
    4. Early termination for error conditions
    """
    # Stream processing for trajectories
    if 'trajectories' in flight_data:
        for traj_name, traj_data in flight_data['trajectories'].items():
            trajectory = traj_data.get('trajectory', [])
            
            # Process in chunks to avoid memory issues
            chunk_size = 1000
            for i in range(0, len(trajectory), chunk_size):
                chunk = trajectory[i:i + chunk_size]
                yield self._process_trajectory_chunk(chunk)
```

### 10.2 Query Optimization

#### 10.2.1 Parameter Indexing
```python
def build_parameter_index(self, flight_data: Dict[str, Any]) -> Dict[str, List[int]]:
    """
    Build indexes for fast parameter lookup:
    - Parameter name to data source mapping
    - Timestamp indexes for time-range queries
    - Value indexes for threshold queries
    """
    index = {}
    
    # Build parameter index
    for param_name in self._get_available_parameters(flight_data):
        index[param_name] = self._find_parameter_sources(flight_data, param_name)
    
    return index
```

#### 10.2.2 Time Range Optimization
```python
def optimize_time_range_query(self, data_points: List[Tuple[float, Any]], 
                            time_range: Tuple[float, float]) -> List[Tuple[float, Any]]:
    """
    Optimize time range queries:
    1. Binary search for start time
    2. Binary search for end time
    3. Return slice of data
    """
    start_time, end_time = time_range
    
    # Binary search for start index
    start_idx = self._binary_search_timestamp(data_points, start_time)
    
    # Binary search for end index
    end_idx = self._binary_search_timestamp(data_points, end_time)
    
    return data_points[start_idx:end_idx]
```

### 10.3 Scalability Considerations

#### 10.3.1 Concurrent Processing
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def process_telemetry_concurrent(self, session_ids: List[str]) -> Dict[str, Any]:
    """
    Process multiple sessions concurrently:
    - Async processing for I/O operations
    - Thread pool for CPU-intensive tasks
    - Rate limiting for external API calls
    """
    async with asyncio.TaskGroup() as tg:
        tasks = []
        for session_id in session_ids:
            task = tg.create_task(self._process_session_async(session_id))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
    
    return dict(zip(session_ids, results))
```

#### 10.3.2 Database Integration
```python
class TelemetryDatabase:
    """
    Database integration for persistent storage:
    - PostgreSQL for structured data
    - Redis for caching
    - Time-series database for telemetry
    """
    def __init__(self):
        self.postgres = self._connect_postgres()
        self.redis = self._connect_redis()
        self.timeseries = self._connect_timeseries()
    
    def store_telemetry_data(self, session_id: str, data: Dict[str, Any]):
        # Store in time-series database
        self.timeseries.insert(session_id, data)
        
        # Cache in Redis
        self.redis.setex(f"telemetry:{session_id}", 3600, json.dumps(data))
        
        # Store metadata in PostgreSQL
        self.postgres.execute(
            "INSERT INTO telemetry_sessions (session_id, created_at, data_size) VALUES (%s, %s, %s)",
            (session_id, datetime.now(), len(json.dumps(data)))
        )
```

---

## Conclusion

The telemetry data system in the UAV Log Viewer Backend API provides comprehensive flight data processing, analysis, and AI-powered insights. Key features include:

- **Comprehensive Data Support**: Handles multiple UAV log formats and data types
- **Advanced Anomaly Detection**: Multi-pattern detection with severity classification
- **Statistical Analysis**: Trend analysis, variance detection, and quality metrics
- **ArduPilot Integration**: Full documentation integration and parameter support
- **Scalable Architecture**: Memory-efficient processing and concurrent operations
- **Quality Assurance**: Data validation, sanitization, and error handling

The system is designed to handle real-world UAV flight data with robust error handling, performance optimization, and comprehensive analysis capabilities.

---

## Appendix

### A. Parameter Reference

#### A.1 GPS Parameters
- **GPS**: Complete GPS position and velocity data
- **GPS_POSITION**: Position coordinates only
- **GPS_COORDINATES**: Lat/lon coordinates
- **GPS_TIME_SERIES**: Time-series GPS data
- **GPS_STATUS**: GPS signal status
- **GPS_SIGNAL**: Signal quality indicators
- **GPS_FIX**: Fix type and quality
- **SATELLITES**: Satellite count data
- **GPS_ACCURACY**: Accuracy metrics (HAcc, VAcc)
- **HDOP/VDOP**: Dilution of precision values

#### A.2 Battery Parameters
- **BATTERY**: Complete battery data
- **BATTERY_VOLTAGE**: Voltage measurements
- **BATTERY_CURRENT**: Current draw
- **BATTERY_REMAINING**: Remaining percentage
- **TEMPERATURE**: Battery temperature

#### A.3 Attitude Parameters
- **ATTITUDE**: Complete attitude data
- **ROLL**: Roll angle
- **PITCH**: Pitch angle
- **YAW**: Yaw angle

#### A.4 Control Parameters
- **RC**: RC input data
- **RC_INPUT**: Control channel data
- **RC_SIGNAL**: Signal strength
- **RSSI**: Signal strength indicator

#### A.5 Flight Parameters
- **MODE**: Flight mode changes
- **FLIGHT_MODE**: Current flight mode
- **MODE_CHANGES**: Mode change history
- **EVENTS**: Flight events
- **PARAMETERS**: Vehicle parameters

### B. Error Codes

#### B.1 Data Validation Errors
- **INVALID_FORMAT**: Data format not recognized
- **MISSING_FIELD**: Required field missing
- **INVALID_TYPE**: Data type mismatch
- **OUT_OF_RANGE**: Value outside expected range

#### B.2 Processing Errors
- **EXTRACTION_FAILED**: Parameter extraction failed
- **ANALYSIS_FAILED**: Statistical analysis failed
- **ANOMALY_DETECTION_FAILED**: Anomaly detection failed
- **DOCUMENTATION_ERROR**: Documentation retrieval failed

### C. Performance Metrics

#### C.1 Processing Times
- **Data Ingestion**: < 100ms for typical flight logs
- **Parameter Extraction**: < 50ms per parameter
- **Statistical Analysis**: < 200ms for full analysis
- **Anomaly Detection**: < 300ms for complete scan

#### C.2 Memory Usage
- **Session Cache**: ~10MB per active session
- **Parameter Cache**: ~1MB per 1000 parameters
- **Anomaly Cache**: ~500KB per analysis
- **Total Memory**: ~50MB for 10 concurrent sessions

### D. Configuration Options

#### D.1 Performance Tuning
```python
# Memory limits
MAX_SESSION_CACHE_SIZE = 1000
MAX_PARAMETER_CACHE_SIZE = 10000
MAX_ANOMALY_CACHE_SIZE = 5000

# Processing limits
MAX_TRAJECTORY_POINTS = 100000
MAX_EVENTS_PER_SESSION = 10000
MAX_PARAMETERS_PER_QUERY = 100

# Timeout settings
DATA_EXTRACTION_TIMEOUT = 30
ANALYSIS_TIMEOUT = 60
DOCUMENTATION_TIMEOUT = 10
```

#### D.2 Quality Thresholds
```python
# Anomaly detection thresholds
SUDDEN_CHANGE_THRESHOLD = 3.0  # 3-sigma rule
VARIANCE_THRESHOLD = 0.5       # 50% coefficient of variation
GPS_ACCURACY_THRESHOLD = 5.0   # 5 meters
BATTERY_LOW_THRESHOLD = 11.0   # 11 volts
TEMPERATURE_HIGH_THRESHOLD = 60.0  # 60°C
```

This documentation provides a comprehensive guide to the telemetry data system, enabling developers to understand, use, and extend the system effectively.
