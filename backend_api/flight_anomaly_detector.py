# flight_anomaly_detector.py - Flight anomaly detection and analysis system

import json
import logging
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import statistics
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class AnomalyContext:
    """Context information for anomaly analysis"""
    parameter: str
    value: Any
    timestamp: float
    expected_range: Optional[Tuple[float, float]] = None
    historical_avg: Optional[float] = None
    trend: Optional[str] = None  # 'increasing', 'decreasing', 'stable', 'volatile'
    severity: str = 'low'  # 'low', 'medium', 'high', 'critical'
    description: str = ""
    related_parameters: List[str] = None

@dataclass
class FlightAnomaly:
    """Represents a detected flight anomaly"""
    anomaly_id: str
    anomaly_type: str
    severity: str
    timestamp: float
    duration: Optional[float] = None
    parameters_affected: List[str] = None
    description: str = ""
    context: Dict[str, Any] = None
    suggested_actions: List[str] = None
    confidence_score: float = 0.0

@dataclass
class TelemetrySummary:
    """Structured summary of telemetry data for LLM analysis"""
    flight_duration: float
    total_data_points: int
    parameters_analyzed: List[str]
    statistical_summary: Dict[str, Dict[str, float]]
    time_series_data: Dict[str, List[Tuple[float, Any]]]
    anomaly_indicators: List[Dict[str, Any]]
    flight_phases: List[Dict[str, Any]]
    quality_metrics: Dict[str, Any]

class FlightAnomalyDetector:
    """Detects and analyzes flight anomalies using flexible, agentic reasoning"""
    
    def __init__(self):
        self.anomaly_patterns = {
            'sudden_changes': ['altitude', 'velocity', 'battery_voltage', 'gps_accuracy'],
            'gradual_drift': ['attitude', 'heading', 'position'],
            'intermittent_issues': ['gps_lock', 'sensor_health', 'communication'],
            'threshold_violations': ['battery_voltage', 'temperature', 'altitude', 'speed'],
            'correlation_anomalies': ['attitude_vs_acceleration', 'gps_vs_velocity', 'battery_vs_consumption']
        }
        
        self.parameter_groups = {
            'navigation': ['gps_lat', 'gps_lon', 'gps_alt', 'gps_accuracy', 'heading', 'ground_speed'],
            'attitude': ['roll', 'pitch', 'yaw', 'roll_rate', 'pitch_rate', 'yaw_rate'],
            'power': ['battery_voltage', 'battery_current', 'battery_remaining', 'power_consumption'],
            'sensors': ['imu_accel_x', 'imu_accel_y', 'imu_accel_z', 'imu_gyro_x', 'imu_gyro_y', 'imu_gyro_z'],
            'flight_modes': ['flight_mode', 'armed_status', 'autopilot_status'],
            'environmental': ['temperature', 'pressure', 'humidity', 'wind_speed', 'wind_direction']
        }
    
    def analyze_flight_data(self, flight_data: Dict[str, Any]) -> TelemetrySummary:
        """Analyze flight data and create structured summary for LLM reasoning"""
        try:
            # Extract time series data
            time_series = self._extract_time_series_data(flight_data)
            
            # Calculate statistical summaries
            statistical_summary = self._calculate_statistical_summary(time_series)
            
            # Identify anomaly indicators
            anomaly_indicators = self._identify_anomaly_indicators(time_series, statistical_summary)
            
            # Identify flight phases
            flight_phases = self._identify_flight_phases(time_series)
            
            # Calculate quality metrics
            quality_metrics = self._calculate_quality_metrics(time_series)
            
            # Calculate flight duration
            flight_duration = self._calculate_flight_duration(time_series)
            
            return TelemetrySummary(
                flight_duration=flight_duration,
                total_data_points=sum(len(data) for data in time_series.values()),
                parameters_analyzed=list(time_series.keys()),
                statistical_summary=statistical_summary,
                time_series_data=time_series,
                anomaly_indicators=anomaly_indicators,
                flight_phases=flight_phases,
                quality_metrics=quality_metrics
            )
            
        except Exception as e:
            logger.error(f"Failed to analyze flight data: {e}")
            return None
    
    def _extract_time_series_data(self, flight_data: Dict[str, Any]) -> Dict[str, List[Tuple[float, Any]]]:
        """Extract time series data from flight data"""
        time_series = defaultdict(list)
        
        # Extract from trajectories
        if 'trajectories' in flight_data:
            for traj_name, traj_data in flight_data['trajectories'].items():
                if 'trajectory' in traj_data:
                    trajectory = traj_data['trajectory']
                    for i, point in enumerate(trajectory):
                        timestamp = i  # Simplified timestamp
                        if len(point) >= 3:
                            time_series['gps_lat'].append((timestamp, point[0]))
                            time_series['gps_lon'].append((timestamp, point[1]))
                            time_series['gps_alt'].append((timestamp, point[2]))
                            if len(point) > 3:
                                time_series['gps_time'].append((timestamp, point[3]))
        
        # Extract GPS metadata
        if 'gps_metadata' in flight_data:
            gps_meta = flight_data['gps_metadata']
            
            # GPS Status changes
            if 'status_changes' in gps_meta:
                for status in gps_meta['status_changes']:
                    timestamp = status.get('timestamp', 0)
                    time_series['gps_status'].append((timestamp, status.get('status', 'unknown')))
                    time_series['gps_fix_type'].append((timestamp, status.get('fix_type', 'unknown')))
            
            # Satellite counts
            if 'satellite_counts' in gps_meta:
                for i, count in enumerate(gps_meta['satellite_counts']):
                    time_series['satellite_count'].append((i, count))
            
            # Signal quality (HDop, VDop)
            if 'signal_quality' in gps_meta:
                for sq in gps_meta['signal_quality']:
                    timestamp = sq.get('timestamp', 0)
                    time_series['hdop'].append((timestamp, sq.get('hdop', 0)))
                    time_series['vdop'].append((timestamp, sq.get('vdop', 0)))
            
            # GPS Accuracy
            if 'accuracy_metrics' in gps_meta:
                for acc in gps_meta['accuracy_metrics']:
                    timestamp = acc.get('timestamp', 0)
                    time_series['hacc'].append((timestamp, acc.get('hacc', 0)))
                    time_series['vacc'].append((timestamp, acc.get('vacc', 0)))
                    time_series['sacc'].append((timestamp, acc.get('sacc', 0)))
        
        # Extract from events
        if 'events' in flight_data:
            for event in flight_data['events']:
                if isinstance(event, dict):
                    timestamp = event.get('timestamp', 0)
                    # Extract various parameters from events
                    for key, value in event.items():
                        if key != 'timestamp' and isinstance(value, (int, float)):
                            time_series[key].append((timestamp, value))
        
        # Extract RC input data
        if 'rc_inputs' in flight_data:
            for rc in flight_data['rc_inputs']:
                timestamp = rc.get('timestamp', 0)
                time_series['rc_signal_strength'].append((timestamp, rc.get('signal_strength', 0)))
                time_series['rc_signal_lost'].append((timestamp, 1 if rc.get('signal_lost', False) else 0))
        
        # Extract from flight mode changes
        if 'flightModeChanges' in flight_data:
            for mode_change in flight_data['flightModeChanges']:
                if len(mode_change) >= 2:
                    timestamp = mode_change[0]
                    mode = mode_change[1]
                    time_series['flight_mode'].append((timestamp, mode))
        
        # Extract from parameters
        if 'params' in flight_data:
            for param_name, param_value in flight_data['params'].items():
                if isinstance(param_value, (int, float)):
                    time_series[param_name].append((0, param_value))

        # Extract attitude series if provided (normalized from frontend)
        if 'attitude_series' in flight_data and isinstance(flight_data['attitude_series'], list):
            for entry in flight_data['attitude_series']:
                if isinstance(entry, dict):
                    ts = entry.get('timestamp', 0)
                    if isinstance(entry.get('roll'), (int, float)):
                        time_series['roll'].append((ts, float(entry['roll'])))
                    if isinstance(entry.get('pitch'), (int, float)):
                        time_series['pitch'].append((ts, float(entry['pitch'])))
                    if isinstance(entry.get('yaw'), (int, float)):
                        time_series['yaw'].append((ts, float(entry['yaw'])))
        
        return dict(time_series)
    
    def _calculate_statistical_summary(self, time_series: Dict[str, List[Tuple[float, Any]]]) -> Dict[str, Dict[str, float]]:
        """Calculate statistical summaries for each parameter"""
        summary = {}
        
        for param_name, data_points in time_series.items():
            if not data_points:
                continue
            
            # Extract numeric values
            values = []
            timestamps = []
            
            for timestamp, value in data_points:
                if isinstance(value, (int, float)):
                    values.append(float(value))
                    timestamps.append(float(timestamp))
                elif isinstance(value, str):
                    # Handle string values (like flight modes)
                    continue
            
            if not values:
                continue
            
            # Calculate statistics
            param_summary = {
                'count': len(values),
                'min': min(values),
                'max': max(values),
                'mean': statistics.mean(values),
                'median': statistics.median(values),
                'std_dev': statistics.stdev(values) if len(values) > 1 else 0.0,
                'range': max(values) - min(values),
                'first_value': values[0],
                'last_value': values[-1],
                'time_span': max(timestamps) - min(timestamps) if timestamps else 0.0
            }
            
            # Calculate trend
            if len(values) > 1:
                # Simple linear trend calculation
                x = np.array(timestamps)
                y = np.array(values)
                if len(x) > 1 and x[-1] != x[0]:
                    slope = np.polyfit(x, y, 1)[0]
                    if slope > 0.01:
                        param_summary['trend'] = 'increasing'
                    elif slope < -0.01:
                        param_summary['trend'] = 'decreasing'
                    else:
                        param_summary['trend'] = 'stable'
                else:
                    param_summary['trend'] = 'stable'
            
            summary[param_name] = param_summary
        
        return summary
    
    def _identify_anomaly_indicators(self, time_series: Dict[str, List[Tuple[float, Any]]], 
                                   statistical_summary: Dict[str, Dict[str, float]]) -> List[Dict[str, Any]]:
        """Identify potential anomaly indicators"""
        indicators = []
        
        # Detect GPS-related anomalies
        indicators.extend(self._detect_gps_anomalies(time_series))
        
        # Detect battery-related anomalies
        indicators.extend(self._detect_battery_anomalies(time_series))
        
        # Detect RC signal anomalies
        indicators.extend(self._detect_rc_signal_anomalies(time_series))
        
        for param_name, data_points in time_series.items():
            if param_name not in statistical_summary:
                continue
            
            stats = statistical_summary[param_name]
            if stats['count'] < 2:
                continue
            
            # Check for sudden changes
            if param_name in self.anomaly_patterns['sudden_changes']:
                sudden_changes = self._detect_sudden_changes(data_points, stats)
                indicators.extend(sudden_changes)
            
            # Check for threshold violations
            if param_name in self.anomaly_patterns['threshold_violations']:
                threshold_violations = self._detect_threshold_violations(data_points, param_name)
                indicators.extend(threshold_violations)
            
            # Check for unusual variance
            if stats['std_dev'] > 0:
                variance_anomalies = self._detect_variance_anomalies(data_points, stats)
                indicators.extend(variance_anomalies)
        
        return indicators
    
    def _detect_sudden_changes(self, data_points: List[Tuple[float, Any]], stats: Dict[str, float]) -> List[Dict[str, Any]]:
        """Detect sudden changes in parameter values"""
        indicators = []
        
        if len(data_points) < 2:
            return indicators
        
        # Calculate change thresholds based on parameter type and statistics
        change_threshold = stats['std_dev'] * 3  # 3-sigma rule
        
        for i in range(1, len(data_points)):
            prev_timestamp, prev_value = data_points[i-1]
            curr_timestamp, curr_value = data_points[i]
            
            if not isinstance(prev_value, (int, float)) or not isinstance(curr_value, (int, float)):
                continue
            
            change = abs(curr_value - prev_value)
            time_diff = curr_timestamp - prev_timestamp
            
            if change > change_threshold and time_diff > 0:
                severity = 'high' if change > change_threshold * 2 else 'medium'
                
                indicators.append({
                    'type': 'sudden_change',
                    'parameter': 'unknown',  # Will be set by caller
                    'timestamp': curr_timestamp,
                    'severity': severity,
                    'change_magnitude': change,
                    'change_threshold': change_threshold,
                    'time_interval': time_diff,
                    'description': f"Sudden change of {change:.2f} detected"
                })
        
        return indicators
    
    def _detect_threshold_violations(self, data_points: List[Tuple[float, Any]], param_name: str) -> List[Dict[str, Any]]:
        """Detect threshold violations for specific parameters"""
        indicators = []
        
        # Define parameter-specific thresholds
        thresholds = {
            'battery_voltage': {'min': 10.0, 'max': 15.0},
            'gps_alt': {'min': -100.0, 'max': 1000.0},
            'gps_accuracy': {'max': 5.0},
            'temperature': {'min': -20.0, 'max': 60.0}
        }
        
        if param_name not in thresholds:
            return indicators
        
        param_thresholds = thresholds[param_name]
        
        for timestamp, value in data_points:
            if not isinstance(value, (int, float)):
                continue
            
            violations = []
            
            if 'min' in param_thresholds and value < param_thresholds['min']:
                violations.append(f"Below minimum threshold ({param_thresholds['min']})")
            
            if 'max' in param_thresholds and value > param_thresholds['max']:
                violations.append(f"Above maximum threshold ({param_thresholds['max']})")
            
            if violations:
                severity = 'critical' if 'Below minimum' in str(violations) else 'high'
                
                indicators.append({
                    'type': 'threshold_violation',
                    'parameter': param_name,
                    'timestamp': timestamp,
                    'severity': severity,
                    'value': value,
                    'thresholds': param_thresholds,
                    'violations': violations,
                    'description': f"Threshold violation: {', '.join(violations)}"
                })
        
        return indicators
    
    def _detect_variance_anomalies(self, data_points: List[Tuple[float, Any]], stats: Dict[str, float]) -> List[Dict[str, Any]]:
        """Detect unusual variance in parameter values"""
        indicators = []
        
        if stats['std_dev'] == 0 or stats['count'] < 10:
            return indicators
        
        # Check for excessive variance
        coefficient_of_variation = stats['std_dev'] / abs(stats['mean']) if stats['mean'] != 0 else 0
        
        if coefficient_of_variation > 0.5:  # 50% coefficient of variation
            indicators.append({
                'type': 'high_variance',
                'parameter': 'unknown',  # Will be set by caller
                'timestamp': 0,  # Global anomaly
                'severity': 'medium',
                'coefficient_of_variation': coefficient_of_variation,
                'std_dev': stats['std_dev'],
                'mean': stats['mean'],
                'description': f"High variance detected (CV: {coefficient_of_variation:.2f})"
            })
        
        return indicators
    
    def _identify_flight_phases(self, time_series: Dict[str, List[Tuple[float, Any]]]) -> List[Dict[str, Any]]:
        """Identify different phases of flight"""
        phases = []
        
        # Simple flight phase detection based on altitude changes
        if 'gps_alt' in time_series:
            alt_data = time_series['gps_alt']
            if len(alt_data) > 10:
                altitudes = [value for _, value in alt_data if isinstance(value, (int, float))]
                timestamps = [timestamp for timestamp, _ in alt_data]
                
                if altitudes:
                    min_alt = min(altitudes)
                    max_alt = max(altitudes)
                    alt_range = max_alt - min_alt
                    
                    # Identify takeoff phase (rapid altitude increase)
                    takeoff_threshold = min_alt + alt_range * 0.1
                    takeoff_points = [(t, a) for t, a in zip(timestamps, altitudes) if a > takeoff_threshold]
                    
                    if takeoff_points:
                        phases.append({
                            'phase': 'takeoff',
                            'start_time': takeoff_points[0][0],
                            'end_time': takeoff_points[-1][0],
                            'altitude_range': (min_alt, takeoff_points[-1][1]),
                            'description': 'Takeoff phase detected'
                        })
                    
                    # Identify cruise phase (stable altitude)
                    cruise_threshold = min_alt + alt_range * 0.3
                    cruise_points = [(t, a) for t, a in zip(timestamps, altitudes) if cruise_threshold <= a <= max_alt - alt_range * 0.1]
                    
                    if cruise_points:
                        phases.append({
                            'phase': 'cruise',
                            'start_time': cruise_points[0][0],
                            'end_time': cruise_points[-1][0],
                            'altitude_range': (cruise_points[0][1], cruise_points[-1][1]),
                            'description': 'Cruise phase detected'
                        })
        
        return phases
    
    def _calculate_quality_metrics(self, time_series: Dict[str, List[Tuple[float, Any]]]) -> Dict[str, Any]:
        """Calculate data quality metrics"""
        metrics = {
            'total_parameters': len(time_series),
            'parameters_with_data': len([p for p in time_series.values() if p]),
            'data_completeness': 0.0,
            'temporal_coverage': 0.0,
            'parameter_correlation': {}
        }
        
        if time_series:
            # Calculate data completeness
            total_possible_points = sum(len(data) for data in time_series.values())
            metrics['data_completeness'] = total_possible_points / (len(time_series) * 100)  # Assuming 100 is expected points
            
            # Calculate temporal coverage
            all_timestamps = set()
            for data_points in time_series.values():
                for timestamp, _ in data_points:
                    all_timestamps.add(timestamp)
            
            if all_timestamps:
                time_span = max(all_timestamps) - min(all_timestamps)
                metrics['temporal_coverage'] = time_span
        
        return metrics
    
    def _calculate_flight_duration(self, time_series: Dict[str, List[Tuple[float, Any]]]) -> float:
        """Calculate total flight duration"""
        all_timestamps = set()
        for data_points in time_series.values():
            for timestamp, _ in data_points:
                all_timestamps.add(timestamp)
        
        if all_timestamps:
            return max(all_timestamps) - min(all_timestamps)
        return 0.0
    
    def generate_anomaly_analysis_prompt(self, telemetry_summary: TelemetrySummary, 
                                       user_question: str) -> str:
        """Generate a prompt for LLM-based anomaly analysis"""
        
        prompt = f"""
You are an expert flight data analyst specializing in UAV anomaly detection. Analyze the following flight data and answer the user's question about potential anomalies.

USER QUESTION: {user_question}

FLIGHT DATA SUMMARY:
- Flight Duration: {telemetry_summary.flight_duration:.1f} seconds
- Total Data Points: {telemetry_summary.total_data_points:,}
- Parameters Analyzed: {', '.join(telemetry_summary.parameters_analyzed)}

STATISTICAL SUMMARY:
"""
        
        # Add statistical summaries for key parameters
        for param_name, stats in telemetry_summary.statistical_summary.items():
            if param_name in ['gps_alt', 'battery_voltage', 'gps_accuracy', 'roll', 'pitch', 'yaw']:
                prompt += f"""
{param_name.upper()}:
  - Range: {stats['min']:.2f} to {stats['max']:.2f}
  - Mean: {stats['mean']:.2f} ± {stats['std_dev']:.2f}
  - Trend: {stats.get('trend', 'unknown')}
  - Data Points: {stats['count']}"""
        
        # Add anomaly indicators
        if telemetry_summary.anomaly_indicators:
            prompt += f"""

POTENTIAL ANOMALY INDICATORS DETECTED:
"""
            for indicator in telemetry_summary.anomaly_indicators[:10]:  # Limit to top 10
                prompt += f"""
- {indicator['type'].upper()}: {indicator['description']}
  Severity: {indicator['severity']}, Timestamp: {indicator['timestamp']}"""
        
        # Add flight phases
        if telemetry_summary.flight_phases:
            prompt += f"""

FLIGHT PHASES IDENTIFIED:
"""
            for phase in telemetry_summary.flight_phases:
                prompt += f"""
- {phase['phase'].upper()}: {phase['description']}
  Duration: {phase['end_time'] - phase['start_time']:.1f}s, Altitude: {phase['altitude_range']}"""
        
        # Add analysis instructions
        prompt += f"""

ANALYSIS INSTRUCTIONS:
1. Look for patterns, trends, and inconsistencies in the data
2. Consider correlations between different parameters
3. Identify potential causes for any anomalies
4. Assess the severity and impact of detected issues
5. Provide specific recommendations for investigation
6. Consider both technical and operational factors

Please provide a comprehensive analysis focusing on:
- Specific anomalies detected
- Potential root causes
- Severity assessment
- Recommended actions
- Areas requiring further investigation

Be thorough but concise, and provide actionable insights.
"""
        
        return prompt

    def _detect_gps_anomalies(self, time_series: Dict[str, List[Tuple[float, Any]]]) -> List[Dict[str, Any]]:
        """Detect GPS-related anomalies with enhanced signal loss detection"""
        anomalies = []
        
        # GPS Signal Loss Detection
        if 'gps_status' in time_series:
            gps_status_data = time_series['gps_status']
            for i, (timestamp, status) in enumerate(gps_status_data):
                if status in ['NO_GPS', 'NO_FIX']:
                    anomalies.append({
                        'type': 'GPS_SIGNAL_LOSS',
                        'severity': 'high',
                        'timestamp': timestamp,
                        'description': f'GPS signal lost: {status}',
                        'confidence': 0.9
                    })
        
        # Enhanced GPS Signal Loss Detection from Events
        if 'gps_event' in time_series:
            gps_event_data = time_series['gps_event']
            for timestamp, event_data in gps_event_data:
                if isinstance(event_data, dict):
                    if 'GPS_SIGNAL_LOSS' in event_data.get('type', ''):
                        anomalies.append({
                            'type': 'GPS_SIGNAL_LOSS',
                            'severity': 'high',
                            'timestamp': timestamp,
                            'description': f'GPS signal loss event: {event_data.get("message", "")}',
                            'confidence': 0.95
                        })
        
        # Satellite Count Anomalies with Trend Analysis
        if 'satellite_count' in time_series:
            sat_data = time_series['satellite_count']
            prev_count = None
            for timestamp, count in sat_data:
                if count < 4:  # Minimum for 3D fix
                    severity = 'critical' if count == 0 else 'medium'
                    anomalies.append({
                        'type': 'LOW_SATELLITE_COUNT',
                        'severity': severity,
                        'timestamp': timestamp,
                        'description': f'Low satellite count: {count} satellites',
                        'confidence': 0.8
                    })
                
                # Detect sudden satellite count drops
                if prev_count is not None and prev_count - count > 3:
                    anomalies.append({
                        'type': 'SATELLITE_COUNT_DROP',
                        'severity': 'high',
                        'timestamp': timestamp,
                        'description': f'Rapid satellite count drop: {prev_count} to {count}',
                        'confidence': 0.85
                    })
                
                prev_count = count
        
        # GPS Accuracy Degradation with Progressive Analysis
        if 'hacc' in time_series:
            hacc_data = time_series['hacc']
            prev_hacc = None
            for timestamp, hacc in hacc_data:
                if hacc > 5.0:  # > 5 meters horizontal accuracy
                    severity = 'critical' if hacc > 20.0 else 'medium'
                    anomalies.append({
                        'type': 'GPS_ACCURACY_DEGRADATION',
                        'severity': severity,
                        'timestamp': timestamp,
                        'description': f'Poor GPS accuracy: {hacc:.1f}m horizontal',
                        'confidence': 0.7
                    })
                
                # Detect rapid accuracy degradation
                if prev_hacc is not None and hacc - prev_hacc > 10.0:
                    anomalies.append({
                        'type': 'GPS_ACCURACY_RAPID_DEGRADATION',
                        'severity': 'high',
                        'timestamp': timestamp,
                        'description': f'Rapid GPS accuracy degradation: {prev_hacc:.1f}m to {hacc:.1f}m',
                        'confidence': 0.8
                    })
                
                prev_hacc = hacc
        
        # HDop Quality Issues with Trend Analysis
        if 'hdop' in time_series:
            hdop_data = time_series['hdop']
            prev_hdop = None
            for timestamp, hdop in hdop_data:
                if hdop > 2.0:  # Poor signal quality
                    severity = 'high' if hdop > 5.0 else 'low'
                    anomalies.append({
                        'type': 'GPS_SIGNAL_QUALITY_POOR',
                        'severity': severity,
                        'timestamp': timestamp,
                        'description': f'Poor GPS signal quality: HDop {hdop:.2f}',
                        'confidence': 0.6
                    })
                
                # Detect rapid HDop increase
                if prev_hdop is not None and hdop - prev_hdop > 2.0:
                    anomalies.append({
                        'type': 'GPS_SIGNAL_QUALITY_RAPID_DEGRADATION',
                        'severity': 'medium',
                        'timestamp': timestamp,
                        'description': f'Rapid GPS signal quality degradation: HDop {prev_hdop:.2f} to {hdop:.2f}',
                        'confidence': 0.7
                    })
                
                prev_hdop = hdop
        
        # GPS Position Jump Detection (potential signal loss indicator)
        if 'gps_lat' in time_series and 'gps_lon' in time_series:
            lat_data = time_series['gps_lat']
            lon_data = time_series['gps_lon']
            
            if len(lat_data) > 1 and len(lon_data) > 1:
                for i in range(1, min(len(lat_data), len(lon_data))):
                    prev_lat, prev_lon = lat_data[i-1][1], lon_data[i-1][1]
                    curr_lat, curr_lon = lat_data[i][1], lon_data[i][1]
                    curr_timestamp = lat_data[i][0]
                    
                    # Calculate distance between consecutive points
                    import math
                    lat_diff = abs(curr_lat - prev_lat)
                    lon_diff = abs(curr_lon - prev_lon)
                    
                    # Rough distance calculation (not precise but good for anomaly detection)
                    distance = math.sqrt(lat_diff**2 + lon_diff**2) * 111000  # Rough meters
                    
                    if distance > 1000:  # > 1km jump
                        anomalies.append({
                            'type': 'GPS_POSITION_JUMP',
                            'severity': 'high',
                            'timestamp': curr_timestamp,
                            'description': f'Large GPS position jump: {distance:.0f}m',
                            'confidence': 0.8
                        })
        
        return anomalies
    
    def _detect_battery_anomalies(self, time_series: Dict[str, List[Tuple[float, Any]]]) -> List[Dict[str, Any]]:
        """Detect battery-related anomalies"""
        anomalies = []
        
        # Battery Voltage Anomalies
        if 'battery_voltage' in time_series:
            voltage_data = time_series['battery_voltage']
            for timestamp, voltage in voltage_data:
                if voltage < 10.5:  # Critical low voltage
                    anomalies.append({
                        'type': 'BATTERY_CRITICAL_LOW',
                        'severity': 'critical',
                        'timestamp': timestamp,
                        'description': f'Critical battery voltage: {voltage:.1f}V',
                        'confidence': 0.95
                    })
                elif voltage < 11.0:  # Low voltage warning
                    anomalies.append({
                        'type': 'BATTERY_LOW',
                        'severity': 'high',
                        'timestamp': timestamp,
                        'description': f'Low battery voltage: {voltage:.1f}V',
                        'confidence': 0.85
                    })
        
        # Temperature Anomalies
        if 'temperature' in time_series:
            temp_data = time_series['temperature']
            for timestamp, temp in temp_data:
                if temp > 60.0:  # High temperature
                    anomalies.append({
                        'type': 'HIGH_TEMPERATURE',
                        'severity': 'high',
                        'timestamp': timestamp,
                        'description': f'High temperature: {temp:.1f}°C',
                        'confidence': 0.8
                    })
                elif temp > 45.0:  # Elevated temperature
                    anomalies.append({
                        'type': 'ELEVATED_TEMPERATURE',
                        'severity': 'medium',
                        'timestamp': timestamp,
                        'description': f'Elevated temperature: {temp:.1f}°C',
                        'confidence': 0.7
                    })
        
        return anomalies
    
    def _detect_rc_signal_anomalies(self, time_series: Dict[str, List[Tuple[float, Any]]]) -> List[Dict[str, Any]]:
        """Detect RC signal-related anomalies"""
        anomalies = []
        
        # RC Signal Loss Detection
        if 'rc_signal_lost' in time_series:
            signal_data = time_series['rc_signal_lost']
            for timestamp, signal_lost in signal_data:
                if signal_lost == 1:  # Signal lost
                    anomalies.append({
                        'type': 'RC_SIGNAL_LOSS',
                        'severity': 'critical',
                        'timestamp': timestamp,
                        'description': 'RC signal lost - vehicle may enter failsafe mode',
                        'confidence': 0.95
                    })
        
        # RC Signal Strength Issues
        if 'rc_signal_strength' in time_series:
            strength_data = time_series['rc_signal_strength']
            for timestamp, strength in strength_data:
                if strength < 20:  # Low signal strength
                    anomalies.append({
                        'type': 'RC_SIGNAL_WEAK',
                        'severity': 'medium',
                        'timestamp': timestamp,
                        'description': f'Weak RC signal: {strength}%',
                        'confidence': 0.7
                    })
        
        return anomalies

# Global anomaly detector instance
_global_anomaly_detector = None

def get_global_anomaly_detector() -> FlightAnomalyDetector:
    """Get the global anomaly detector instance"""
    global _global_anomaly_detector
    if _global_anomaly_detector is None:
        _global_anomaly_detector = FlightAnomalyDetector()
    return _global_anomaly_detector
