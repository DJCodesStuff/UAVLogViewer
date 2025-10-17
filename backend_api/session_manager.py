from typing import Dict, Optional
from models import SessionData, FlightDataSummary
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages user sessions and flight data"""
    
    def __init__(self):
        self.sessions: Dict[str, SessionData] = {}
    
    def create_session(self, session_id: str) -> SessionData:
        """Create a new session"""
        session = SessionData(session_id=session_id)
        self.sessions[session_id] = session
        logger.info(f"Created session: {session_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[SessionData]:
        """Get session by ID"""
        return self.sessions.get(session_id)
    
    def get_or_create_session(self, session_id: str) -> SessionData:
        """Get existing session or create new one"""
        session = self.get_session(session_id)
        if session is None:
            session = self.create_session(session_id)
        return session
    
    def store_flight_data(self, session_id: str, flight_data: Dict) -> FlightDataSummary:
        """Store flight data for a session"""
        session = self.get_or_create_session(session_id)
        session.flight_data = flight_data
        session.update_activity()
        
        # Create summary
        summary = self._create_flight_summary(session_id, flight_data)
        logger.info(f"Stored flight data for session {session_id}: {len(summary.available_parameters)} parameters")
        return summary
    
    def _create_flight_summary(self, session_id: str, flight_data: Dict) -> FlightDataSummary:
        """Create a summary of available flight data"""
        summary = FlightDataSummary(session_id=session_id)
        
        # Basic info
        summary.vehicle_type = flight_data.get('vehicle')
        summary.log_type = flight_data.get('logType')
        
        # Check available data types
        available_params = []
        
        if flight_data.get('trajectories'):
            summary.has_gps = True
            available_params.extend(['GPS', 'GPS_POSITION', 'ALTITUDE', 'COORDINATES'])
        
        if flight_data.get('batterySeries') or flight_data.get('battery_series'):
            summary.has_battery = True
            available_params.extend(['BATTERY', 'BATTERY_VOLTAGE', 'BATTERY_CURRENT'])
        
        if flight_data.get('timeAttitude'):
            summary.has_attitude = True
            available_params.extend(['ATTITUDE', 'ROLL', 'PITCH', 'YAW'])
        
        if flight_data.get('events'):
            summary.has_events = True
            available_params.append('EVENTS')
        
        if flight_data.get('flightModeChanges'):
            available_params.append('FLIGHT_MODES')
        
        if flight_data.get('params'):
            available_params.append('PARAMETERS')
        
        if flight_data.get('gps_metadata'):
            available_params.extend(['GPS_STATUS', 'GPS_SIGNAL_QUALITY'])
        
        summary.available_parameters = list(set(available_params))
        
        # Calculate data points
        trajectories = flight_data.get('trajectories', {})
        for traj_name, traj_data in trajectories.items():
            if isinstance(traj_data, dict) and 'trajectory' in traj_data:
                summary.data_points += len(traj_data['trajectory'])
        
        return summary
    
    def add_message(self, session_id: str, role: str, content: str):
        """Add a message to session conversation"""
        session = self.get_or_create_session(session_id)
        session.add_message(role, content)
    
    def get_conversation_history(self, session_id: str, limit: int = 10):
        """Get conversation history for a session"""
        session = self.get_session(session_id)
        if session:
            return session.get_recent_history(limit)
        return []
    
    def cleanup_old_sessions(self, max_age_seconds: int = 3600):
        """Remove sessions older than max_age_seconds"""
        current_time = datetime.now().timestamp()
        expired = [
            sid for sid, session in self.sessions.items()
            if current_time - session.last_activity > max_age_seconds
        ]
        for sid in expired:
            del self.sessions[sid]
            logger.info(f"Removed expired session: {sid}")

