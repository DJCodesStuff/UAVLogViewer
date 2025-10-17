from typing import Dict, Any, List, Optional, Tuple
import statistics
import logging

logger = logging.getLogger(__name__)


class TelemetryService:
    """Service for retrieving and analyzing telemetry data"""
    
    def __init__(self, session_manager):
        self.session_manager = session_manager
    
    def get_parameter_data(
        self, 
        session_id: str, 
        parameter: str,
        time_range: Optional[Tuple[float, float]] = None
    ) -> Dict[str, Any]:
        """Retrieve telemetry data for a specific parameter"""
        session = self.session_manager.get_session(session_id)
        if not session or not session.flight_data:
            return {'error': 'No flight data available'}
        
        flight_data = session.flight_data
        result = {
            'parameter': parameter,
            'data': [],
            'statistics': {},
            'metadata': {}
        }
        
        # Extract data based on parameter type
        if parameter.upper() in ['GPS', 'GPS_POSITION', 'COORDINATES']:
            result = self._extract_gps_data(flight_data, time_range)
            # Attach GPS quality metadata if available
            gps_quality = self._extract_gps_quality(flight_data)
            if gps_quality:
                result['metadata']['quality'] = gps_quality
        elif parameter.upper() in ['ALTITUDE', 'ALT']:
            result = self._extract_altitude_data(flight_data, time_range)
        elif parameter.upper() in ['BATTERY', 'BATTERY_VOLTAGE']:
            result = self._extract_battery_data(flight_data, time_range)
        elif parameter.upper() in ['ATTITUDE', 'ROLL', 'PITCH', 'YAW']:
            result = self._extract_attitude_data(flight_data, parameter, time_range)
        elif parameter.upper() == 'EVENTS':
            result = self._extract_events(flight_data, time_range)
        elif parameter.upper() in ['FLIGHT_MODES', 'MODE']:
            result = self._extract_flight_modes(flight_data)
        elif parameter.upper() in ['GPS_QUALITY', 'GPS_STATUS', 'GPS_SIGNAL_QUALITY']:
            result = self._extract_gps_quality(flight_data) or {
                'parameter': 'GPS_QUALITY',
                'data': [],
                'metadata': {},
                'statistics': {},
                'count': 0
            }
        
        return result
    
    def _extract_gps_data(self, flight_data: Dict, time_range: Optional[Tuple[float, float]]) -> Dict:
        """Extract GPS position data"""
        trajectories = flight_data.get('trajectories', {})
        data_points = []
        
        for traj_name, traj_data in trajectories.items():
            if isinstance(traj_data, dict) and 'trajectory' in traj_data:
                trajectory = traj_data['trajectory']
                for point in trajectory:
                    if len(point) >= 4:  # [lon, lat, alt, timestamp]
                        timestamp = point[3]
                        if time_range and not (time_range[0] <= timestamp <= time_range[1]):
                            continue
                        data_points.append({
                            'timestamp': timestamp,
                            'longitude': point[0],
                            'latitude': point[1],
                            'altitude': point[2]
                        })
        
        # Calculate statistics
        if data_points:
            altitudes = [p['altitude'] for p in data_points]
            stats = self._calculate_statistics(altitudes)
        else:
            stats = {}
        
        return {
            'parameter': 'GPS',
            'data': data_points,
            'statistics': stats,
            'count': len(data_points)
        }
    
    def _extract_altitude_data(self, flight_data: Dict, time_range: Optional[Tuple[float, float]]) -> Dict:
        """Extract altitude data"""
        gps_data = self._extract_gps_data(flight_data, time_range)
        altitudes = [(p['timestamp'], p['altitude']) for p in gps_data['data']]
        
        return {
            'parameter': 'ALTITUDE',
            'data': altitudes,
            'statistics': gps_data['statistics'],
            'count': len(altitudes)
        }

    def _extract_gps_quality(self, flight_data: Dict) -> Dict[str, Any]:
        """Extract GPS signal quality/status metrics from gps_metadata if present.
        Returns a dictionary with aggregated metrics such as hacc stats and status changes.
        """
        gps_meta = flight_data.get('gps_metadata', {}) or {}
        if not isinstance(gps_meta, dict) or not gps_meta:
            return {}

        quality: Dict[str, Any] = {
            'statuses': [],
            'latest_status': None,
            'accuracy': {},
            'satellites': None,
            'hdop': None
        }

        # Status changes history
        status_changes = gps_meta.get('status_changes', []) or []
        if isinstance(status_changes, list) and status_changes:
            # Normalize to dicts with timestamp and status
            normalized = []
            for sc in status_changes:
                if isinstance(sc, dict):
                    normalized.append({
                        'timestamp': sc.get('timestamp'),
                        'status': sc.get('status')
                    })
            quality['statuses'] = normalized
            quality['latest_status'] = normalized[-1]['status'] if normalized else None

        # Accuracy metrics (e.g., hacc)
        accuracy_metrics = gps_meta.get('accuracy_metrics', []) or []
        hacc_values: List[float] = []
        for m in accuracy_metrics:
            if isinstance(m, dict) and isinstance(m.get('hacc'), (int, float)):
                hacc_values.append(float(m['hacc']))
        if hacc_values:
            quality['accuracy']['hacc'] = self._calculate_statistics(hacc_values)

        # Optional: satellites and hdop if present in metadata
        if isinstance(gps_meta.get('satellites'), (int, float)):
            quality['satellites'] = gps_meta.get('satellites')
        if isinstance(gps_meta.get('hdop'), (int, float)):
            quality['hdop'] = gps_meta.get('hdop')

        # Remove empty sections
        if not quality['statuses']:
            quality.pop('statuses')
        if not quality['accuracy']:
            quality.pop('accuracy')
        if quality.get('latest_status') is None:
            quality.pop('latest_status', None)
        if quality.get('satellites') is None:
            quality.pop('satellites', None)
        if quality.get('hdop') is None:
            quality.pop('hdop', None)

        return quality
    
    def _extract_battery_data(self, flight_data: Dict, time_range: Optional[Tuple[float, float]]) -> Dict:
        """Extract battery data"""
        battery_series = flight_data.get('batterySeries', []) or flight_data.get('battery_series', [])
        data_points = []
        
        for entry in battery_series:
            if isinstance(entry, dict):
                timestamp = entry.get('timestamp')
                if time_range and timestamp and not (time_range[0] <= timestamp <= time_range[1]):
                    continue
                data_points.append({
                    'timestamp': timestamp,
                    'voltage': entry.get('voltage'),
                    'current': entry.get('current'),
                    'remaining': entry.get('remaining'),
                    'temperature': entry.get('temperature')
                })
        
        # Calculate statistics for voltage
        if data_points:
            voltages = [p['voltage'] for p in data_points if p.get('voltage') is not None]
            stats = self._calculate_statistics(voltages) if voltages else {}
        else:
            stats = {}
        
        return {
            'parameter': 'BATTERY',
            'data': data_points,
            'statistics': stats,
            'count': len(data_points)
        }
    
    def _extract_attitude_data(self, flight_data: Dict, parameter: str, time_range: Optional[Tuple[float, float]]) -> Dict:
        """Extract attitude data (roll, pitch, yaw)"""
        time_attitude = flight_data.get('timeAttitude', {})
        data_points = []
        
        for timestamp, attitude in time_attitude.items():
            ts = float(timestamp)
            if time_range and not (time_range[0] <= ts <= time_range[1]):
                continue
            
            if isinstance(attitude, (list, tuple)) and len(attitude) >= 3:
                data_points.append({
                    'timestamp': ts,
                    'roll': attitude[0],
                    'pitch': attitude[1],
                    'yaw': attitude[2]
                })
        
        # Sort by timestamp
        data_points.sort(key=lambda x: x['timestamp'])
        
        # Calculate statistics for requested parameter
        if data_points and parameter.upper() in ['ROLL', 'PITCH', 'YAW']:
            param_lower = parameter.lower()
            values = [p[param_lower] for p in data_points]
            stats = self._calculate_statistics(values)
        else:
            stats = {}
        
        return {
            'parameter': parameter.upper(),
            'data': data_points,
            'statistics': stats,
            'count': len(data_points)
        }
    
    def _extract_events(self, flight_data: Dict, time_range: Optional[Tuple[float, float]]) -> Dict:
        """Extract flight events"""
        events = flight_data.get('events', [])
        filtered_events = []
        
        for event in events:
            if isinstance(event, dict):
                timestamp = event.get('timestamp')
                if time_range and timestamp and not (time_range[0] <= timestamp <= time_range[1]):
                    continue
                filtered_events.append(event)
        
        return {
            'parameter': 'EVENTS',
            'data': filtered_events,
            'count': len(filtered_events)
        }
    
    def _extract_flight_modes(self, flight_data: Dict) -> Dict:
        """Extract flight mode changes"""
        mode_changes = flight_data.get('flightModeChanges', [])
        
        return {
            'parameter': 'FLIGHT_MODES',
            'data': mode_changes,
            'count': len(mode_changes)
        }
    
    def _calculate_statistics(self, values: List[float]) -> Dict[str, float]:
        """Calculate basic statistics for a list of values"""
        if not values:
            return {}
        
        try:
            return {
                'min': min(values),
                'max': max(values),
                'mean': statistics.mean(values),
                'median': statistics.median(values),
                'std_dev': statistics.stdev(values) if len(values) > 1 else 0,
                'count': len(values)
            }
        except Exception as e:
            logger.error(f"Error calculating statistics: {e}")
            return {}
    
    def detect_anomalies(self, session_id: str, parameters: List[str] = None) -> List[Dict[str, Any]]:
        """Detect anomalies using LLM-driven intelligent analysis"""
        session = self.session_manager.get_session(session_id)
        if not session or not session.flight_data:
            return []
        
        # Get comprehensive flight data summary for LLM analysis
        flight_summary = self._create_comprehensive_flight_summary(session_id, session.flight_data)
        
        # Use LLM to detect anomalies intelligently
        anomalies = self._llm_anomaly_detection(flight_summary)
        
        return anomalies

    # -------------------- RAG support: build per-session vector docs --------------------
    def create_vector_documents(self, session_id: str, flight_data: Dict[str, Any]) -> Tuple[List[str], List[Dict[str, Any]]]:
        """Create a set of text chunks and payloads representing the session's telemetry for vector indexing.
        Returns (texts, payloads). Each payload includes the original text under 'text' and metadata.
        """
        texts: List[str] = []
        payloads: List[Dict[str, Any]] = []
        CHUNK_SIZE = 500  # number of rows per vector chunk for large series

        def _chunk_list(items: List[Any], n: int) -> List[List[Any]]:
            if not isinstance(items, list) or n <= 0:
                return []
            return [items[i:i + n] for i in range(0, len(items), n)]

        # Summary document
        summary = self._create_comprehensive_flight_summary(session_id, flight_data)
        summary_text = (
            f"SESSION {session_id} SUMMARY\n"
            f"Vehicle: {summary['metadata'].get('vehicle_type','Unknown')}\n"
            f"Log Type: {summary['metadata'].get('log_type','Unknown')}\n"
            f"Duration: {summary['metadata'].get('duration','Unknown')}\n"
            f"Data Availability: {summary['data_availability']}\n"
        )
        texts.append(summary_text)
        payloads.append({
            'type': 'summary',
            'session_id': session_id,
            'text': summary_text
        })

        # GPS chunk
        if flight_data.get('trajectories'):
            gps = self._extract_gps_data(flight_data, None)
            gps_text = (
                f"SESSION {session_id} GPS\n"
                f"Points: {gps.get('count',0)}\n"
                f"Stats: {gps.get('statistics',{})}\n"
            )
            texts.append(gps_text)
            payloads.append({'type': 'gps', 'session_id': session_id, 'text': gps_text})

            # Raw GPS samples in chunks
            gps_points = gps.get('data', [])
            for idx, chunk in enumerate(_chunk_list(gps_points, CHUNK_SIZE)):
                lines = []
                for p in chunk:
                    if isinstance(p, dict):
                        lines.append(f"{p.get('timestamp')},{p.get('latitude')},{p.get('longitude')},{p.get('altitude')}")
                if lines:
                    chunk_text = (
                        f"SESSION {session_id} GPS POINTS CHUNK {idx}\n" + "\n".join(lines)
                    )
                    texts.append(chunk_text)
                    payloads.append({'type': 'gps_points', 'session_id': session_id, 'chunk_index': idx, 'text': chunk_text})

        # Altitude chunk
        if flight_data.get('trajectories'):
            alt = self._extract_altitude_data(flight_data, None)
            alt_text = (
                f"SESSION {session_id} ALTITUDE\n"
                f"Points: {alt.get('count',0)}\n"
                f"Stats: {alt.get('statistics',{})}\n"
            )
            texts.append(alt_text)
            payloads.append({'type': 'altitude', 'session_id': session_id, 'text': alt_text})

            # Raw altitude samples in chunks (timestamp, altitude)
            alt_points = alt.get('data', [])
            for idx, chunk in enumerate(_chunk_list(alt_points, CHUNK_SIZE)):
                lines = []
                for p in chunk:
                    if isinstance(p, (list, tuple)) and len(p) >= 2:
                        lines.append(f"{p[0]},{p[1]}")
                if lines:
                    chunk_text = (
                        f"SESSION {session_id} ALTITUDE POINTS CHUNK {idx}\n" + "\n".join(lines)
                    )
                    texts.append(chunk_text)
                    payloads.append({'type': 'altitude_points', 'session_id': session_id, 'chunk_index': idx, 'text': chunk_text})

        # Battery chunk
        if flight_data.get('batterySeries') or flight_data.get('battery_series'):
            bat = self._extract_battery_data(flight_data, None)
            bat_text = (
                f"SESSION {session_id} BATTERY\n"
                f"Points: {bat.get('count',0)}\n"
                f"Voltage Stats: {bat.get('statistics',{})}\n"
            )
            texts.append(bat_text)
            payloads.append({'type': 'battery', 'session_id': session_id, 'text': bat_text})

            # Raw battery samples in chunks
            bat_points = bat.get('data', [])
            for idx, chunk in enumerate(_chunk_list(bat_points, CHUNK_SIZE)):
                lines = []
                for p in chunk:
                    if isinstance(p, dict):
                        lines.append(
                            f"{p.get('timestamp')},{p.get('voltage')},{p.get('current')},{p.get('remaining')},{p.get('temperature')}"
                        )
                if lines:
                    chunk_text = (
                        f"SESSION {session_id} BATTERY SERIES CHUNK {idx}\n" + "\n".join(lines)
                    )
                    texts.append(chunk_text)
                    payloads.append({'type': 'battery_series', 'session_id': session_id, 'chunk_index': idx, 'text': chunk_text})

        # Attitude chunk
        if flight_data.get('timeAttitude'):
            att = self._extract_attitude_data(flight_data, 'ATTITUDE', None)
            att_text = (
                f"SESSION {session_id} ATTITUDE\n"
                f"Points: {att.get('count',0)}\n"
                f"Stats: {att.get('statistics',{})}\n"
            )
            texts.append(att_text)
            payloads.append({'type': 'attitude', 'session_id': session_id, 'text': att_text})

            # Raw attitude samples in chunks (timestamp,roll,pitch,yaw)
            att_points = att.get('data', [])
            for idx, chunk in enumerate(_chunk_list(att_points, CHUNK_SIZE)):
                lines = []
                for p in chunk:
                    if isinstance(p, dict):
                        lines.append(f"{p.get('timestamp')},{p.get('roll')},{p.get('pitch')},{p.get('yaw')}")
                if lines:
                    chunk_text = (
                        f"SESSION {session_id} ATTITUDE POINTS CHUNK {idx}\n" + "\n".join(lines)
                    )
                    texts.append(chunk_text)
                    payloads.append({'type': 'attitude_points', 'session_id': session_id, 'chunk_index': idx, 'text': chunk_text})

        # Events chunk
        if flight_data.get('events'):
            events = self._extract_events(flight_data, None)
            # Include first 10 event lines
            lines = []
            for e in events.get('data', [])[:10]:
                if isinstance(e, dict):
                    lines.append(f"- {e.get('timestamp')}: {e.get('type')} - {e.get('message')}")
            ev_text = (
                f"SESSION {session_id} EVENTS\n"
                f"Count: {events.get('count',0)}\n" + "\n".join(lines)
            )
            texts.append(ev_text)
            payloads.append({'type': 'events', 'session_id': session_id, 'text': ev_text})

            # All events chunked
            all_event_lines = []
            for e in events.get('data', []):
                if isinstance(e, dict):
                    all_event_lines.append(f"{e.get('timestamp')},{e.get('type')},{e.get('severity')},{e.get('message')}")
            for idx, chunk in enumerate(_chunk_list(all_event_lines, CHUNK_SIZE)):
                if chunk:
                    chunk_text = (
                        f"SESSION {session_id} EVENTS CHUNK {idx}\n" + "\n".join(chunk)
                    )
                    texts.append(chunk_text)
                    payloads.append({'type': 'events_all', 'session_id': session_id, 'chunk_index': idx, 'text': chunk_text})

        # Flight modes chunk
        if flight_data.get('flightModeChanges'):
            modes = flight_data.get('flightModeChanges', [])
            mode_lines = []
            for m in modes[:20]:
                if isinstance(m, list) and len(m) >= 2:
                    mode_lines.append(f"- {m[0]}: {m[1]}")
            modes_text = (
                f"SESSION {session_id} FLIGHT MODES\n" + "\n".join(mode_lines)
            )
            texts.append(modes_text)
            payloads.append({'type': 'flight_modes', 'session_id': session_id, 'text': modes_text})

            # All modes expanded
            mode_all_lines = []
            for m in modes:
                if isinstance(m, list) and len(m) >= 2:
                    mode_all_lines.append(f"{m[0]},{m[1]}")
            for idx, chunk in enumerate(_chunk_list(mode_all_lines, CHUNK_SIZE)):
                if chunk:
                    chunk_text = (
                        f"SESSION {session_id} FLIGHT MODES CHUNK {idx}\n" + "\n".join(chunk)
                    )
                    texts.append(chunk_text)
                    payloads.append({'type': 'flight_modes_all', 'session_id': session_id, 'chunk_index': idx, 'text': chunk_text})

        # Params chunk (flatten)
        if isinstance(flight_data.get('params'), dict):
            param_lines = []
            for k, v in list(flight_data['params'].items())[:1000]:
                param_lines.append(f"{k}={v}")
            for idx, chunk in enumerate(_chunk_list(param_lines, CHUNK_SIZE)):
                if chunk:
                    chunk_text = (
                        f"SESSION {session_id} PARAMS CHUNK {idx}\n" + "\n".join(chunk)
                    )
                    texts.append(chunk_text)
                    payloads.append({'type': 'params', 'session_id': session_id, 'chunk_index': idx, 'text': chunk_text})

        # Text messages
        if isinstance(flight_data.get('textMessages'), list):
            lines = []
            for msg in flight_data['textMessages']:
                if isinstance(msg, dict):
                    lines.append(f"{msg.get('timestamp')},{msg.get('name')},{msg.get('value')}")
            for idx, chunk in enumerate(_chunk_list(lines, CHUNK_SIZE)):
                if chunk:
                    chunk_text = (
                        f"SESSION {session_id} TEXT MESSAGES CHUNK {idx}\n" + "\n".join(chunk)
                    )
                    texts.append(chunk_text)
                    payloads.append({'type': 'text_messages', 'session_id': session_id, 'chunk_index': idx, 'text': chunk_text})

        # Named floats list
        if isinstance(flight_data.get('namedFloats'), list):
            nf_lines = []
            for name in flight_data['namedFloats']:
                nf_lines.append(str(name))
            for idx, chunk in enumerate(_chunk_list(nf_lines, CHUNK_SIZE)):
                if chunk:
                    chunk_text = (
                        f"SESSION {session_id} NAMED FLOATS CHUNK {idx}\n" + "\n".join(chunk)
                    )
                    texts.append(chunk_text)
                    payloads.append({'type': 'named_floats', 'session_id': session_id, 'chunk_index': idx, 'text': chunk_text})

        # GPS metadata chunk
        if isinstance(flight_data.get('gps_metadata'), dict):
            gpsq = self._extract_gps_quality(flight_data)
            gpsq_text = f"SESSION {session_id} GPS QUALITY\n{gpsq}"
            texts.append(gpsq_text)
            payloads.append({'type': 'gps_quality', 'session_id': session_id, 'text': gpsq_text})

        # Mission / fences basic dumps (if present)
        if isinstance(flight_data.get('mission'), list) and flight_data['mission']:
            m_text = f"SESSION {session_id} MISSION SIZE {len(flight_data['mission'])}"
            texts.append(m_text)
            payloads.append({'type': 'mission', 'session_id': session_id, 'text': m_text})
        if isinstance(flight_data.get('fences'), list) and flight_data['fences']:
            f_text = f"SESSION {session_id} FENCES SIZE {len(flight_data['fences'])}"
            texts.append(f_text)
            payloads.append({'type': 'fences', 'session_id': session_id, 'text': f_text})

        return texts, payloads
    
    def _create_comprehensive_flight_summary(self, session_id: str, flight_data: Dict) -> Dict[str, Any]:
        """Create a comprehensive, structured summary of flight data for LLM analysis"""
        summary = {
            'session_id': session_id,
            'metadata': {
                'vehicle_type': flight_data.get('vehicle', 'Unknown'),
                'log_type': flight_data.get('logType', 'Unknown'),
                'start_time': flight_data.get('metadata', {}).get('startTime'),
                'duration': flight_data.get('metadata', {}).get('duration')
            },
            'data_availability': {
                'has_gps': bool(flight_data.get('trajectories')),
                'has_battery': bool(flight_data.get('batterySeries') or flight_data.get('battery_series')),
                'has_attitude': bool(flight_data.get('timeAttitude')),
                'has_events': bool(flight_data.get('events')),
                'has_flight_modes': bool(flight_data.get('flightModeChanges')),
                'has_gps_metadata': bool(flight_data.get('gps_metadata'))
            },
            'telemetry_data': {},
            'events': flight_data.get('events', []),
            'flight_modes': flight_data.get('flightModeChanges', []),
            'gps_metadata': flight_data.get('gps_metadata', {})
        }
        
        # Extract and structure GPS data
        if flight_data.get('trajectories'):
            gps_data = self._extract_gps_data(flight_data, None)
            summary['telemetry_data']['gps'] = {
                'data_points': gps_data.get('count', 0),
                'statistics': gps_data.get('statistics', {}),
                'sample_data': gps_data.get('data', [])[:10]  # First 10 points
            }
        
        # Extract and structure battery data
        if flight_data.get('batterySeries') or flight_data.get('battery_series'):
            battery_data = self._extract_battery_data(flight_data, None)
            summary['telemetry_data']['battery'] = {
                'data_points': battery_data.get('count', 0),
                'statistics': battery_data.get('statistics', {}),
                'sample_data': battery_data.get('data', [])[:10]  # First 10 points
            }
        
        # Extract and structure attitude data
        if flight_data.get('timeAttitude'):
            attitude_data = self._extract_attitude_data(flight_data, 'ATTITUDE', None)
            summary['telemetry_data']['attitude'] = {
                'data_points': attitude_data.get('count', 0),
                'statistics': attitude_data.get('statistics', {}),
                'sample_data': attitude_data.get('data', [])[:10]  # First 10 points
            }
        
        return summary
    
    def _llm_anomaly_detection(self, flight_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Use LLM to intelligently detect anomalies in flight data"""
        try:
            # Import here to avoid circular imports
            from gemini_service import GeminiService
            from config import Config
            
            gemini = GeminiService(Config.GOOGLE_API_KEY, Config.GEMINI_MODEL)
            
            # Create structured prompt for anomaly detection
            system_prompt = """You are an expert UAV flight safety analyst. Your task is to intelligently detect anomalies, safety concerns, and unusual patterns in flight data.

ANALYSIS APPROACH:
- Look for sudden changes, inconsistencies, and patterns that could indicate problems
- Consider context and relationships between different data streams
- Focus on safety-critical issues that could affect flight operations
- Be thorough but avoid false positives from normal flight variations

ANOMALY TYPES TO CONSIDER:
- GPS signal issues (loss, degradation, accuracy problems)
- Battery problems (voltage drops, temperature spikes, power issues)
- Attitude anomalies (unusual orientations, control issues)
- Flight mode changes (unexpected transitions, failsafe activations)
- Event patterns (error sequences, warning clusters)
- Data inconsistencies (missing data, unrealistic values)
- Performance issues (efficiency, range, endurance)

RESPONSE FORMAT:
Return a JSON array of anomalies, each with:
- type: Anomaly category (GPS_ISSUE, BATTERY_PROBLEM, etc.)
- severity: critical, high, medium, low
- timestamp: When it occurred (if available)
- description: Clear explanation of the issue
- confidence: How confident you are (0.0-1.0)
- context: Additional context about why this is concerning

Be specific and reference actual data values when possible."""
            
            # Format the flight summary for the LLM
            data_context = f"""FLIGHT DATA SUMMARY:

Vehicle: {flight_summary['metadata']['vehicle_type']}
Duration: {flight_summary['metadata'].get('duration', 'Unknown')} seconds
Start Time: {flight_summary['metadata'].get('start_time', 'Unknown')}

DATA AVAILABILITY:
- GPS Data: {flight_summary['data_availability']['has_gps']}
- Battery Data: {flight_summary['data_availability']['has_battery']}
- Attitude Data: {flight_summary['data_availability']['has_attitude']}
- Events: {flight_summary['data_availability']['has_events']}
- Flight Modes: {flight_summary['data_availability']['has_flight_modes']}

TELEMETRY DATA:
"""
            
            # Add telemetry data details
            for param, data in flight_summary['telemetry_data'].items():
                data_context += f"\n{param.upper()}:"
                data_context += f"\n  Data Points: {data['data_points']}"
                if data.get('statistics'):
                    stats = data['statistics']
                    for key, value in stats.items():
                        if isinstance(value, float):
                            data_context += f"\n  {key}: {value:.2f}"
                        else:
                            data_context += f"\n  {key}: {value}"
            
            # Add events
            if flight_summary['events']:
                data_context += f"\n\nFLIGHT EVENTS ({len(flight_summary['events'])}):"
                for event in flight_summary['events']:
                    if isinstance(event, dict):
                        data_context += f"\n- {event.get('type', 'Unknown')}: {event.get('message', 'No message')} (Severity: {event.get('severity', 'Unknown')})"
            
            # Add flight mode changes
            if flight_summary['flight_modes']:
                data_context += f"\n\nFLIGHT MODE CHANGES ({len(flight_summary['flight_modes'])}):"
                for mode_change in flight_summary['flight_modes']:
                    if isinstance(mode_change, list) and len(mode_change) >= 2:
                        data_context += f"\n- {mode_change[1]} at timestamp {mode_change[0]}"
            
            user_prompt = f"{data_context}\n\nPlease analyze this flight data and identify any anomalies, safety concerns, or unusual patterns. Return your analysis as a JSON array of anomalies."
            
            # Get LLM response
            response = gemini.chat(user_prompt, system_prompt)
            
            # Parse the response (expecting JSON)
            try:
                import json
                # Clean the response to extract JSON
                response = response.strip()
                if response.startswith('```json'):
                    response = response[7:]
                if response.endswith('```'):
                    response = response[:-3]
                
                anomalies = json.loads(response)
                if not isinstance(anomalies, list):
                    anomalies = [anomalies]
                
                return anomalies
                
            except json.JSONDecodeError:
                # If JSON parsing fails, create a fallback anomaly
                return [{
                    'type': 'ANALYSIS_ERROR',
                    'severity': 'low',
                    'description': f'Could not parse LLM anomaly analysis: {response[:100]}...',
                    'confidence': 0.1
                }]
                
        except Exception as e:
            logger.error(f"Error in LLM anomaly detection: {e}")
            return [{
                'type': 'ANALYSIS_ERROR',
                'severity': 'low',
                'description': f'Error during anomaly analysis: {str(e)}',
                'confidence': 0.1
            }]
    
    def _detect_gps_anomalies(self, flight_data: Dict) -> List[Dict]:
        """Detect GPS-specific anomalies"""
        anomalies = []
        gps_metadata = flight_data.get('gps_metadata', {})
        
        # Check for GPS signal loss
        status_changes = gps_metadata.get('status_changes', [])
        for change in status_changes:
            status = change.get('status', '')
            if 'NO_GPS' in status or 'NO_FIX' in status:
                anomalies.append({
                    'type': 'GPS_SIGNAL_LOSS',
                    'severity': 'high',
                    'timestamp': change.get('timestamp'),
                    'description': f'GPS signal lost: {status}'
                })
        
        # Check GPS accuracy
        accuracy_metrics = gps_metadata.get('accuracy_metrics', [])
        for metric in accuracy_metrics:
            hacc = metric.get('hacc')
            if hacc and hacc > 5.0:
                severity = 'critical' if hacc > 20.0 else 'medium'
                anomalies.append({
                    'type': 'GPS_ACCURACY_DEGRADATION',
                    'severity': severity,
                    'timestamp': metric.get('timestamp'),
                    'description': f'Poor GPS accuracy: {hacc:.1f}m horizontal'
                })
        
        # Also check events for GPS-related issues
        events = flight_data.get('events', [])
        for event in events:
            if isinstance(event, dict):
                event_type = event.get('type', '').upper()
                message = event.get('message', '').upper()
                if 'GPS' in event_type or 'GPS' in message:
                    if 'LOST' in message or 'NO' in message:
                        anomalies.append({
                            'type': 'GPS_SIGNAL_LOSS',
                            'severity': 'high',
                            'timestamp': event.get('timestamp'),
                            'description': event.get('message', 'GPS signal issue')
                        })
        
        return anomalies
    
    def _detect_battery_anomalies(self, flight_data: Dict) -> List[Dict]:
        """Detect battery-related anomalies"""
        anomalies = []
        battery_series = flight_data.get('batterySeries', []) or flight_data.get('battery_series', [])
        
        for entry in battery_series:
            if isinstance(entry, dict):
                voltage = entry.get('voltage')
                temp = entry.get('temperature')
                timestamp = entry.get('timestamp')
                
                # Low voltage
                if voltage and voltage < 10.5:
                    anomalies.append({
                        'type': 'BATTERY_CRITICAL_LOW',
                        'severity': 'critical',
                        'timestamp': timestamp,
                        'description': f'Critical battery voltage: {voltage:.1f}V'
                    })
                
                # High temperature
                if temp and temp > 60.0:
                    anomalies.append({
                        'type': 'HIGH_TEMPERATURE',
                        'severity': 'high',
                        'timestamp': timestamp,
                        'description': f'High battery temperature: {temp:.1f}°C'
                    })
        
        # Also check events for battery-related issues
        events = flight_data.get('events', [])
        for event in events:
            if isinstance(event, dict):
                event_type = event.get('type', '').upper()
                message = event.get('message', '').upper()
                if 'BATTERY' in event_type or 'BATTERY' in message or 'TEMP' in message:
                    anomalies.append({
                        'type': 'BATTERY_ISSUE',
                        'severity': event.get('severity', 'medium'),
                        'timestamp': event.get('timestamp'),
                        'description': event.get('message', 'Battery issue detected')
                    })
        
        return anomalies

