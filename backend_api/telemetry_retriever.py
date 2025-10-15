# telemetry_retriever.py - Dynamic telemetry information retrieval

import json
import re
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import logging
import requests
from urllib.parse import urljoin
from flight_anomaly_detector import get_global_anomaly_detector, TelemetrySummary
from ardupilot_docs import get_global_docs_retriever

logger = logging.getLogger(__name__)

@dataclass
class TelemetryParameter:
    """Structure for telemetry parameters"""
    name: str
    description: str
    units: str
    category: str
    ardupilot_doc_url: Optional[str] = None
    example_values: List[Any] = None

@dataclass
class TelemetryQuery:
    """Structure for telemetry queries"""
    parameter: str
    time_range: Optional[Tuple[float, float]] = None
    aggregation: str = "raw"  # raw, min, max, avg, std
    filter_conditions: Dict[str, Any] = None

class ArduPilotDocumentationRetriever:
    """Retrieves and caches ArduPilot documentation"""
    
    def __init__(self):
        self.base_url = "https://ardupilot.org/plane/docs/logmessages.html"
        self.cache: Dict[str, str] = {}
        self.parameter_docs: Dict[str, Dict[str, Any]] = {}
        self.last_fetch = 0
        self.cache_duration = 3600  # 1 hour
    
    def get_parameter_documentation(self, parameter: str) -> Dict[str, Any]:
        """Get documentation for a specific parameter"""
        if time.time() - self.last_fetch > self.cache_duration:
            self._refresh_documentation()
        
        return self.parameter_docs.get(parameter, {
            "name": parameter,
            "description": f"Parameter {parameter} - documentation not available",
            "units": "unknown",
            "category": "unknown"
        })
    
    def _refresh_documentation(self):
        """Refresh documentation from ArduPilot website"""
        try:
            # For now, we'll use a simplified approach
            # In a real implementation, you'd parse the HTML from the URL
            self._load_common_parameters()
            self.last_fetch = time.time()
        except Exception as e:
            logger.warning(f"Failed to refresh ArduPilot documentation: {e}")
    
    def _load_common_parameters(self):
        """Load common ArduPilot parameters with comprehensive documentation"""
        try:
            # Get comprehensive documentation from ArduPilot docs retriever
            docs_retriever = get_global_docs_retriever()
            
            # Load all available parameters
            all_params = docs_retriever.get_all_parameters()
            
            for param_name in all_params:
                param_doc = docs_retriever.get_parameter_documentation(param_name)
                
                # Convert to our format
                self.parameter_docs[param_name] = {
                    "name": param_name,
                    "description": param_doc.get("description", f"ArduPilot {param_name} parameter"),
                    "units": self._extract_units_from_fields(param_doc.get("fields", {})),
                    "category": self._categorize_parameter(param_name),
                    "fields": param_doc.get("fields", {}),
                    "documentation_url": f"https://ardupilot.org/plane/docs/logmessages.html#{param_name.lower()}",
                    "source": param_doc.get("source", "ardupilot.org")
                }
            
            logger.info(f"Loaded {len(self.parameter_docs)} ArduPilot parameters with comprehensive documentation")
            
        except Exception as e:
            logger.warning(f"Failed to load comprehensive documentation: {e}")
            self._load_fallback_parameters()
    
    def _extract_units_from_fields(self, fields: Dict[str, Dict[str, str]]) -> str:
        """Extract units information from field documentation"""
        units = set()
        for field_info in fields.values():
            if "units" in field_info:
                units.add(field_info["units"])
        
        if units:
            return ", ".join(sorted(units))
        return "unknown"
    
    def _categorize_parameter(self, param_name: str) -> str:
        """Categorize parameter based on name"""
        param_upper = param_name.upper()
        
        if param_upper in ["GPS", "GPA", "POS", "POSI"]:
            return "position"
        elif param_upper in ["BAT", "PWR", "POW"]:
            return "power"
        elif param_upper in ["ATT", "IMU", "ACC", "GYR"]:
            return "attitude"
        elif param_upper in ["RCIN", "RSSI", "RC"]:
            return "control"
        elif param_upper in ["MODE", "NAV", "WP"]:
            return "navigation"
        elif param_upper in ["ERR", "MSG", "STAT"]:
            return "diagnostics"
        elif param_upper in ["BARO", "COMP", "MAG"]:
            return "sensors"
        else:
            return "telemetry"
    
    def _load_fallback_parameters(self):
        """Load fallback parameters when comprehensive loading fails"""
        fallback_params = {
            "GPS": {
                "name": "GPS",
                "description": "GPS position and velocity data",
                "units": "degrees, meters, m/s",
                "category": "position",
                "fields": {
                    "Status": {"description": "GPS fix status", "units": "enum"},
                    "NSats": {"description": "Number of satellites", "units": "count"},
                    "HDop": {"description": "Horizontal dilution of precision", "units": "ratio"},
                    "Lat": {"description": "Latitude", "units": "degrees"},
                    "Lng": {"description": "Longitude", "units": "degrees"},
                    "Alt": {"description": "Altitude", "units": "meters"}
                },
                "documentation_url": "https://ardupilot.org/plane/docs/logmessages.html#gps",
                "source": "fallback"
            },
            "BAT": {
                "name": "BAT",
                "description": "Battery voltage and current",
                "units": "volts, amperes",
                "category": "power",
                "fields": {
                    "Volt": {"description": "Battery voltage", "units": "volts"},
                    "Curr": {"description": "Battery current", "units": "amperes"}
                },
                "documentation_url": "https://ardupilot.org/plane/docs/logmessages.html#bat",
                "source": "fallback"
            }
        }
        
        self.parameter_docs.update(fallback_params)
        logger.info("Loaded fallback parameter documentation")

class DynamicTelemetryRetriever:
    """Dynamically retrieves telemetry information based on queries"""
    
    def __init__(self):
        self.doc_retriever = get_global_docs_retriever()
        # Force load fallback documentation
        self.doc_retriever._load_fallback_documentation()
        self.flight_data_cache: Dict[str, Dict[str, Any]] = {}
    
    def set_flight_data(self, session_id: str, flight_data: Dict[str, Any]):
        """Set flight data for a session"""
        self.flight_data_cache[session_id] = flight_data
        logger.info(f"Set flight data for session {session_id}")
    
    def get_flight_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get flight data for a session"""
        return self.flight_data_cache.get(session_id)
    
    def query_telemetry(self, session_id: str, query: TelemetryQuery) -> Dict[str, Any]:
        """Query telemetry data based on the query parameters"""
        flight_data = self.get_flight_data(session_id)
        if not flight_data:
            return {
                "error": "No flight data available",
                "suggestion": "Please load flight data first"
            }
        
        # Get parameter documentation
        param_doc = self.doc_retriever.get_parameter_documentation(query.parameter)
        
        # Ensure documentation has required fields
        if 'units' not in param_doc:
            param_doc['units'] = self._extract_units_from_fields(param_doc.get('fields', {}))
        if 'category' not in param_doc:
            param_doc['category'] = self._categorize_parameter(query.parameter)
        
        # Extract relevant data based on parameter
        telemetry_data = self._extract_parameter_data(flight_data, query.parameter)
        
        if not telemetry_data:
            return {
                "error": f"Parameter {query.parameter} not found in flight data",
                "available_parameters": self._get_available_parameters(flight_data),
                "documentation": param_doc
            }
        
        # Apply time range filter if specified
        if query.time_range:
            telemetry_data = self._filter_by_time_range(telemetry_data, query.time_range)
        
        # Apply aggregation if specified
        if query.aggregation != "raw":
            telemetry_data = self._apply_aggregation(telemetry_data, query.aggregation)
        
        # Get field-specific documentation
        field_docs = {}
        if telemetry_data and isinstance(telemetry_data, list) and len(telemetry_data) > 0:
            first_data = telemetry_data[0]
            for field_name in first_data.keys():
                if field_name not in ['timestamp', 'type']:
                    field_doc = self.doc_retriever.get_field_documentation(query.parameter, field_name)
                    field_docs[field_name] = field_doc
        
        return {
            "parameter": query.parameter,
            "documentation": param_doc,
            "field_documentation": field_docs,
            "data": telemetry_data,
            "time_range": query.time_range,
            "aggregation": query.aggregation,
            "data_points": len(telemetry_data) if isinstance(telemetry_data, list) else 1,
            "ardupilot_reference": f"https://ardupilot.org/plane/docs/logmessages.html#{query.parameter.lower()}"
        }
    
    def _extract_units_from_fields(self, fields: Dict[str, Dict[str, str]]) -> str:
        """Extract units information from field documentation"""
        units = set()
        for field_info in fields.values():
            if "units" in field_info:
                units.add(field_info["units"])
        
        if units:
            return ", ".join(sorted(units))
        return "unknown"
    
    def _categorize_parameter(self, param_name: str) -> str:
        """Categorize parameter based on name"""
        param_upper = param_name.upper()
        
        if param_upper in ["GPS", "GPA", "POS", "POSI"]:
            return "position"
        elif param_upper in ["BAT", "PWR", "POW"]:
            return "power"
        elif param_upper in ["ATT", "IMU", "ACC", "GYR"]:
            return "attitude"
        elif param_upper in ["RCIN", "RSSI", "RC"]:
            return "control"
        elif param_upper in ["MODE", "NAV", "WP"]:
            return "navigation"
        elif param_upper in ["ERR", "MSG", "STAT"]:
            return "diagnostics"
        elif param_upper in ["BARO", "COMP", "MAG"]:
            return "sensors"
        else:
            return "telemetry"
    
    def _extract_parameter_data(self, flight_data: Dict[str, Any], parameter: str) -> List[Dict[str, Any]]:
        """Extract data for a specific parameter from flight data with comprehensive parsing"""
        parameter_upper = parameter.upper()
        extracted_data = []
        
        # GPS-related parameters
        if parameter_upper in ['GPS', 'GPS_POSITION', 'GPS_COORDINATES']:
            if 'trajectories' in flight_data:
                for traj_name, traj_data in flight_data['trajectories'].items():
                    if 'trajectory' in traj_data:
                        trajectory = traj_data['trajectory']
                        for i, point in enumerate(trajectory):
                            if len(point) >= 3:
                                extracted_data.append({
                                    "timestamp": i,
                                    "lat": point[0] if len(point) > 0 else None,
                                    "lon": point[1] if len(point) > 1 else None,
                                    "alt": point[2] if len(point) > 2 else None,
                                    "time": point[3] if len(point) > 3 else None,
                                    "type": "gps_position"
                                })
        
        # Enhanced GPS data extraction from time series data
        elif parameter_upper in ['GPS_TIME_SERIES', 'GPS_ALL']:
            if 'trajectories' in flight_data:
                for traj_name, traj_data in flight_data['trajectories'].items():
                    if 'trajectory' in traj_data:
                        trajectory = traj_data['trajectory']
                        for i, point in enumerate(trajectory):
                            if len(point) >= 3:
                                extracted_data.append({
                                    "timestamp": i,
                                    "lat": point[0] if len(point) > 0 else None,
                                    "lon": point[1] if len(point) > 1 else None,
                                    "alt": point[2] if len(point) > 2 else None,
                                    "time": point[3] if len(point) > 3 else None,
                                    "type": "gps_time_series"
                                })
        
        # GPS Status and Signal Quality
        elif parameter_upper in ['GPS_STATUS', 'GPS_SIGNAL', 'GPS_FIX']:
            if 'gps_metadata' in flight_data:
                gps_meta = flight_data['gps_metadata']
                if 'status_changes' in gps_meta:
                    for status in gps_meta['status_changes']:
                        extracted_data.append({
                            "timestamp": status.get('timestamp', 0),
                            "status": status.get('status', 'unknown'),
                            "fix_type": status.get('fix_type', 'unknown'),
                            "type": "gps_status"
                        })
            
            # Also check for GPS data in events
            if 'events' in flight_data:
                for event in flight_data['events']:
                    if isinstance(event, dict):
                        event_type = event.get('type', '').upper()
                        if 'GPS' in event_type or 'SIGNAL' in event_type:
                            extracted_data.append({
                                "timestamp": event.get('timestamp', 0),
                                "status": event.get('status', 'unknown'),
                                "message": event.get('message', ''),
                                "satellites": event.get('satellites', 0),
                                "type": "gps_event"
                            })
        
        # Satellite Count
        elif parameter_upper in ['SATELLITES', 'SATS', 'NSATS', 'GPS_SATELLITES']:
            if 'gps_metadata' in flight_data:
                gps_meta = flight_data['gps_metadata']
                if 'satellite_counts' in gps_meta:
                    for i, count in enumerate(gps_meta['satellite_counts']):
                        extracted_data.append({
                            "timestamp": i,
                            "satellite_count": count,
                            "type": "satellite_count"
                        })
        
        # GPS Accuracy
        elif parameter_upper in ['GPS_ACCURACY', 'HACC', 'VACC', 'GPS_PRECISION']:
            if 'gps_metadata' in flight_data:
                gps_meta = flight_data['gps_metadata']
                if 'accuracy_metrics' in gps_meta:
                    for acc in gps_meta['accuracy_metrics']:
                        extracted_data.append({
                            "timestamp": acc.get('timestamp', 0),
                            "hacc": acc.get('hacc', 0),
                            "vacc": acc.get('vacc', 0),
                            "sacc": acc.get('sacc', 0),
                            "type": "gps_accuracy"
                        })
        
        # GPS Signal Quality (HDop, VDop)
        elif parameter_upper in ['HDOP', 'VDOP', 'GPS_QUALITY', 'SIGNAL_QUALITY']:
            if 'gps_metadata' in flight_data:
                gps_meta = flight_data['gps_metadata']
                if 'signal_quality' in gps_meta:
                    for sq in gps_meta['signal_quality']:
                        extracted_data.append({
                            "timestamp": sq.get('timestamp', 0),
                            "hdop": sq.get('hdop', 0),
                            "vdop": sq.get('vdop', 0),
                            "type": "signal_quality"
                        })
        
        # Battery Data
        elif parameter_upper in ['BATTERY', 'BAT', 'VOLTAGE', 'BATTERY_VOLTAGE']:
            if 'events' in flight_data:
                for event in flight_data['events']:
                    if isinstance(event, dict) and 'battery_voltage' in event:
                        extracted_data.append({
                            "timestamp": event.get('timestamp', 0),
                            "voltage": event.get('battery_voltage', 0),
                            "type": "battery_voltage"
                        })
        
        # Temperature Data
        elif parameter_upper in ['TEMPERATURE', 'TEMP', 'BATTERY_TEMP']:
            if 'events' in flight_data:
                for event in flight_data['events']:
                    if isinstance(event, dict) and 'temperature' in event:
                        extracted_data.append({
                            "timestamp": event.get('timestamp', 0),
                            "temperature": event.get('temperature', 0),
                            "type": "temperature"
                        })
        
        # RC Input Data
        elif parameter_upper in ['RC', 'RC_INPUT', 'RC_SIGNAL', 'RSSI']:
            if 'rc_inputs' in flight_data:
                for rc in flight_data['rc_inputs']:
                    extracted_data.append({
                        "timestamp": rc.get('timestamp', 0),
                        "signal_strength": rc.get('signal_strength', 0),
                        "signal_lost": rc.get('signal_lost', False),
                        "type": "rc_input"
                    })
        
        # Flight Duration
        elif parameter_upper in ['FLIGHT_TIME', 'DURATION', 'FLIGHT_DURATION']:
            if 'trajectories' in flight_data:
                for traj_name, traj_data in flight_data['trajectories'].items():
                    if 'trajectory' in traj_data:
                        trajectory = traj_data['trajectory']
                        if len(trajectory) > 1 and len(trajectory[0]) > 3:
                            start_time = trajectory[0][3]
                            end_time = trajectory[-1][3]
                            duration = (end_time - start_time) / 1000.0
                            extracted_data.append({
                                "timestamp": 0,
                                "duration_seconds": duration,
                                "start_time": start_time,
                                "end_time": end_time,
                                "type": "flight_duration"
                            })
        
        # Altitude Data
        elif parameter_upper in ['ALTITUDE', 'ALT', 'HEIGHT']:
            if 'trajectories' in flight_data:
                for traj_name, traj_data in flight_data['trajectories'].items():
                    if 'trajectory' in traj_data:
                        trajectory = traj_data['trajectory']
                        for i, point in enumerate(trajectory):
                            if len(point) > 2:
                                extracted_data.append({
                                    "timestamp": i,
                                    "altitude": point[2],
                                    "type": "altitude"
                                })
        
        # Flight Mode Changes
        elif parameter_upper in ['MODE', 'FLIGHT_MODE', 'MODE_CHANGES']:
            if 'flightModeChanges' in flight_data:
                for mode_change in flight_data['flightModeChanges']:
                    if len(mode_change) >= 2:
                        extracted_data.append({
                            "timestamp": mode_change[0],
                            "mode": mode_change[1],
                            "type": "flight_mode"
                        })
        
        # Enhanced event extraction with comprehensive parsing
        elif parameter_upper in ['EVENTS', 'ALL_EVENTS', 'FLIGHT_EVENTS']:
            if 'events' in flight_data:
                for i, event in enumerate(flight_data['events']):
                    if isinstance(event, dict):
                        extracted_data.append({
                            "timestamp": event.get('timestamp', i),
                            "event_type": event.get('type', 'unknown'),
                            "message": event.get('message', ''),
                            "severity": event.get('severity', 'info'),
                            "event_data": event,
                            "type": "flight_event"
                        })
        
        # Comprehensive parameter extraction
        elif parameter_upper in ['PARAMETERS', 'ALL_PARAMETERS', 'VEHICLE_PARAMS']:
            if 'params' in flight_data:
                for param_name, param_value in flight_data['params'].items():
                    extracted_data.append({
                        "timestamp": 0,
                        "parameter_name": param_name,
                        "parameter_value": param_value,
                        "parameter_type": type(param_value).__name__,
                        "type": "vehicle_parameter"
                    })
        
        # Flight mode comprehensive extraction
        elif parameter_upper in ['FLIGHT_MODES', 'MODE_HISTORY', 'ALL_MODES']:
            if 'flightModeChanges' in flight_data:
                for i, mode_change in enumerate(flight_data['flightModeChanges']):
                    if len(mode_change) >= 2:
                        extracted_data.append({
                            "timestamp": mode_change[0],
                            "mode": mode_change[1],
                            "mode_index": i,
                            "type": "flight_mode_change"
                        })
        
        # Mission data extraction
        elif parameter_upper in ['MISSION', 'MISSION_DATA', 'WAYPOINTS']:
            if 'mission' in flight_data:
                for i, mission_item in enumerate(flight_data['mission']):
                    extracted_data.append({
                        "timestamp": i,
                        "mission_item": mission_item,
                        "item_index": i,
                        "type": "mission_data"
                    })
        
        # Generic event search with enhanced parsing
        else:
            # Try to find parameter in various data sources
            found_data = False
            
            # Check in events
            if 'events' in flight_data and not found_data:
                for event in flight_data['events']:
                    if isinstance(event, dict) and parameter_upper in str(event).upper():
                        extracted_data.append({
                            "timestamp": event.get('timestamp', 0),
                            "event": event,
                            "type": "event"
                        })
                        found_data = True
            
            # Check in parameters
            if 'params' in flight_data and not found_data:
                for param_name, param_value in flight_data['params'].items():
                    if parameter_upper in param_name.upper():
                        extracted_data.append({
                            "timestamp": 0,
                            "parameter_name": param_name,
                            "parameter_value": param_value,
                            "type": "parameter_match"
                        })
                        found_data = True
            
            # Check in trajectories for additional data
            if 'trajectories' in flight_data and not found_data:
                for traj_name, traj_data in flight_data['trajectories'].items():
                    if parameter_upper in traj_name.upper():
                        if 'trajectory' in traj_data:
                            trajectory = traj_data['trajectory']
                            for i, point in enumerate(trajectory):
                                extracted_data.append({
                                    "timestamp": i,
                                    "trajectory_name": traj_name,
                                    "point_data": point,
                                    "type": "trajectory_match"
                                })
                            found_data = True
        
        return extracted_data
    
    def _get_available_parameters(self, flight_data: Dict[str, Any]) -> List[str]:
        """Get comprehensive list of available parameters in flight data"""
        available = []
        
        # GPS and trajectory data
        if 'trajectories' in flight_data:
            available.extend(['GPS', 'GPS_POSITION', 'GPS_COORDINATES', 'GPS_TIME_SERIES', 'GPS_ALL'])
            for traj_name in flight_data['trajectories'].keys():
                available.append(f'TRAJECTORY_{traj_name.upper()}')
        
        # GPS metadata
        if 'gps_metadata' in flight_data:
            gps_meta = flight_data['gps_metadata']
            if 'status_changes' in gps_meta:
                available.extend(['GPS_STATUS', 'GPS_SIGNAL', 'GPS_FIX'])
            if 'satellite_counts' in gps_meta:
                available.extend(['SATELLITES', 'SATS', 'NSATS', 'GPS_SATELLITES'])
            if 'accuracy_metrics' in gps_meta:
                available.extend(['GPS_ACCURACY', 'HACC', 'VACC', 'GPS_PRECISION'])
            if 'signal_quality' in gps_meta:
                available.extend(['HDOP', 'VDOP', 'GPS_QUALITY', 'SIGNAL_QUALITY'])
        
        # Flight modes
        if 'flightModeChanges' in flight_data:
            available.extend(['MODE', 'FLIGHT_MODE', 'MODE_CHANGES', 'FLIGHT_MODES', 'MODE_HISTORY', 'ALL_MODES'])
        
        # Events
        if 'events' in flight_data:
            available.extend(['EVENTS', 'ALL_EVENTS', 'FLIGHT_EVENTS'])
            # Extract specific event types
            for event in flight_data['events']:
                if isinstance(event, dict) and 'type' in event:
                    available.append(f'EVENT_{event["type"].upper()}')
        
        # Parameters
        if 'params' in flight_data:
            available.extend(['PARAMETERS', 'ALL_PARAMETERS', 'VEHICLE_PARAMS'])
            available.extend(list(flight_data['params'].keys()))
        
        # Mission data
        if 'mission' in flight_data:
            available.extend(['MISSION', 'MISSION_DATA', 'WAYPOINTS'])
        
        # RC inputs
        if 'rc_inputs' in flight_data:
            available.extend(['RC', 'RC_INPUT', 'RC_SIGNAL', 'RSSI'])
        
        # Vehicle information
        if 'vehicle' in flight_data:
            available.append('VEHICLE_INFO')
        
        # Metadata
        if 'metadata' in flight_data:
            available.append('METADATA')
        
        # Time-based parameters
        available.extend(['FLIGHT_TIME', 'DURATION', 'FLIGHT_DURATION'])
        available.extend(['ALTITUDE', 'ALT', 'HEIGHT'])
        
        # Remove duplicates and sort
        return sorted(list(set(available)))
    
    def _filter_by_time_range(self, data: List[Dict[str, Any]], time_range: Tuple[float, float]) -> List[Dict[str, Any]]:
        """Filter data by time range"""
        start_time, end_time = time_range
        return [
            item for item in data 
            if start_time <= item.get('timestamp', 0) <= end_time
        ]
    
    def _apply_aggregation(self, data: List[Dict[str, Any]], aggregation: str) -> Dict[str, Any]:
        """Apply aggregation to data"""
        if not data:
            return {}
        
        # Extract values from different field names
        values = []
        for item in data:
            # Try different possible field names
            for field in ['value', 'voltage', 'temperature', 'altitude', 'satellite_count', 'hacc', 'vacc', 'hdop', 'vdop']:
                if field in item and isinstance(item[field], (int, float)):
                    values.append(item[field])
                    break
        
        if not values:
            return {"raw": data}
        
        if aggregation == "min":
            return {"min": min(values)}
        elif aggregation == "max":
            return {"max": max(values)}
        elif aggregation == "avg":
            return {"avg": sum(values) / len(values)}
        elif aggregation == "std":
            if len(values) > 1:
                mean = sum(values) / len(values)
                variance = sum((x - mean) ** 2 for x in values) / len(values)
                return {"std": variance ** 0.5}
            return {"std": 0}
        
        return {"raw": data}
    
    def get_telemetry_summary(self, session_id: str) -> Dict[str, Any]:
        """Get a summary of available telemetry data"""
        flight_data = self.get_flight_data(session_id)
        if not flight_data:
            return {"error": "No flight data available"}
        
        summary = {
            "session_id": session_id,
            "available_parameters": self._get_available_parameters(flight_data),
            "data_sources": []
        }
        
        if 'trajectories' in flight_data:
            summary["data_sources"].append({
                "type": "trajectories",
                "count": len(flight_data['trajectories']),
                "description": "GPS trajectory data"
            })
        
        if 'events' in flight_data:
            summary["data_sources"].append({
                "type": "events",
                "count": len(flight_data['events']),
                "description": "Flight events and messages"
            })
        
        if 'flightModeChanges' in flight_data:
            summary["data_sources"].append({
                "type": "mode_changes",
                "count": len(flight_data['flightModeChanges']),
                "description": "Flight mode changes"
            })
        
        if 'params' in flight_data:
            summary["data_sources"].append({
                "type": "parameters",
                "count": len(flight_data['params']),
                "description": "Vehicle parameters"
            })
        
        return summary
    
    def analyze_flight_anomalies(self, session_id: str, user_question: str = "") -> Dict[str, Any]:
        """Analyze flight data for anomalies using the anomaly detector"""
        flight_data = self.get_flight_data(session_id)
        if not flight_data:
            return {"error": "No flight data available for anomaly analysis"}
        
        try:
            # Get anomaly detector
            anomaly_detector = get_global_anomaly_detector()
            
            # Analyze flight data
            telemetry_summary = anomaly_detector.analyze_flight_data(flight_data)
            if not telemetry_summary:
                return {"error": "Failed to analyze flight data"}
            
            # Generate analysis prompt for LLM
            analysis_prompt = anomaly_detector.generate_anomaly_analysis_prompt(telemetry_summary, user_question)
            
            return {
                "session_id": session_id,
                "telemetry_summary": {
                    "flight_duration": telemetry_summary.flight_duration,
                    "total_data_points": telemetry_summary.total_data_points,
                    "parameters_analyzed": telemetry_summary.parameters_analyzed,
                    "anomaly_indicators_count": len(telemetry_summary.anomaly_indicators),
                    "flight_phases_count": len(telemetry_summary.flight_phases)
                },
                "anomaly_indicators": telemetry_summary.anomaly_indicators,
                "flight_phases": telemetry_summary.flight_phases,
                "statistical_summary": telemetry_summary.statistical_summary,
                "analysis_prompt": analysis_prompt,
                "quality_metrics": telemetry_summary.quality_metrics
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze flight anomalies: {e}")
            return {"error": f"Anomaly analysis failed: {str(e)}"}
    
    def get_structured_telemetry_data(self, session_id: str) -> Dict[str, Any]:
        """Get structured telemetry data for LLM analysis"""
        flight_data = self.get_flight_data(session_id)
        if not flight_data:
            return {"error": "No flight data available"}
        
        try:
            anomaly_detector = get_global_anomaly_detector()
            telemetry_summary = anomaly_detector.analyze_flight_data(flight_data)
            
            if not telemetry_summary:
                return {"error": "Failed to structure telemetry data"}
            
            # Create a structured summary for LLM consumption
            structured_data = {
                "flight_overview": {
                    "duration_seconds": telemetry_summary.flight_duration,
                    "total_data_points": telemetry_summary.total_data_points,
                    "parameters_available": telemetry_summary.parameters_analyzed
                },
                "key_parameters": {},
                "anomaly_summary": {
                    "total_indicators": len(telemetry_summary.anomaly_indicators),
                    "high_severity": len([i for i in telemetry_summary.anomaly_indicators if i.get('severity') == 'high']),
                    "critical_severity": len([i for i in telemetry_summary.anomaly_indicators if i.get('severity') == 'critical'])
                },
                "flight_phases": telemetry_summary.flight_phases,
                "data_quality": telemetry_summary.quality_metrics
            }
            
            # Add key parameter summaries
            key_params = ['gps_alt', 'battery_voltage', 'gps_accuracy', 'roll', 'pitch', 'yaw', 'ground_speed']
            for param in key_params:
                if param in telemetry_summary.statistical_summary:
                    stats = telemetry_summary.statistical_summary[param]
                    structured_data["key_parameters"][param] = {
                        "min": stats['min'],
                        "max": stats['max'],
                        "mean": stats['mean'],
                        "std_dev": stats['std_dev'],
                        "trend": stats.get('trend', 'unknown'),
                        "data_points": stats['count']
                    }
            
            return structured_data
            
        except Exception as e:
            logger.error(f"Failed to structure telemetry data: {e}")
            return {"error": f"Failed to structure data: {str(e)}"}

# Global telemetry retriever instance
_global_telemetry_retriever = None

def get_global_telemetry_retriever() -> DynamicTelemetryRetriever:
    """Get the global telemetry retriever instance"""
    global _global_telemetry_retriever
    if _global_telemetry_retriever is None:
        _global_telemetry_retriever = DynamicTelemetryRetriever()
    return _global_telemetry_retriever
