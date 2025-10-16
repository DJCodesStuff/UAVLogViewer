from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
import time
from datetime import datetime
import json
import os
from typing import Dict, List, Any
import logging
from llm_config import LangGraphReactAgent
from rag_manager import get_global_rag_manager
from telemetry_retriever import get_global_telemetry_retriever
from conversation_state import get_global_conversation_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# In-memory storage for sessions and flight data
sessions: Dict[str, Dict[str, Any]] = {}
flight_data_cache: Dict[str, Dict[str, Any]] = {}

# Global LLM agent instance
llm_agent = None

def initialize_llm_agent():
    """Initialize the LLM agent"""
    global llm_agent
    try:
        llm_agent = LangGraphReactAgent()
        logger.info("LLM agent initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize LLM agent: {str(e)}")
        llm_agent = None

class SessionManager:
    """Manages multiple chat sessions with flight data context"""
    
    def __init__(self):
        self.sessions = sessions
        self.flight_data = flight_data_cache
        self.llm_agents = {}  # Store LLM agents per session
    
    def create_session(self, session_id: str = None) -> str:
        """Create a new chat session"""
        if not session_id:
            session_id = str(uuid.uuid4())
        
        self.sessions[session_id] = {
            'id': session_id,
            'created_at': datetime.now().isoformat(),
            'last_activity': datetime.now().isoformat(),
            'messages': [],
            'flight_data': None,
            'context': {
                'has_flight_data': False,
                'vehicle_type': None,
                'flight_duration': None,
                'start_time': None,
                'total_events': 0,
                'flight_modes': [],
                'gps_points': 0,
                'altitude_range': None,
                'speed_range': None
            }
        }
        
        logger.info(f"Created new session: {session_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get session data"""
        return self.sessions.get(session_id)
    
    def update_session_activity(self, session_id: str):
        """Update last activity timestamp"""
        if session_id in self.sessions:
            self.sessions[session_id]['last_activity'] = datetime.now().isoformat()
    
    def add_message(self, session_id: str, message: str, sender: str = 'user'):
        """Add a message to the session"""
        if session_id not in self.sessions:
            return False
        
        message_data = {
            'id': str(uuid.uuid4()),
            'text': message,
            'sender': sender,
            'timestamp': datetime.now().isoformat()
        }
        
        self.sessions[session_id]['messages'].append(message_data)
        self.update_session_activity(session_id)
        
        logger.info(f"Added {sender} message to session {session_id}")
        return True
    
    def store_flight_data(self, session_id: str, flight_data: Dict[str, Any]):
        """Store flight data for a session"""
        if session_id not in self.sessions:
            return False
        
        # Normalize incoming flight data to backend-friendly schema
        normalized = self._normalize_flight_data(flight_data)

        # Store the flight data
        self.flight_data[session_id] = normalized
        self.sessions[session_id]['flight_data'] = normalized
        
        # Immediately sync to telemetry retriever cache
        try:
            telemetry_retriever = get_global_telemetry_retriever()
            telemetry_retriever.set_flight_data(session_id, normalized)
        except Exception as e:
            logger.warning(f"Failed to set telemetry data for session {session_id}: {e}")
        
        # Update context with flight data summary
        context = self.sessions[session_id]['context']
        context['has_flight_data'] = True
        
        # Extract key information from flight data
        if 'vehicle' in normalized:
            context['vehicle_type'] = normalized['vehicle']
        
        if 'metadata' in normalized and normalized['metadata']:
            if 'startTime' in normalized['metadata']:
                context['start_time'] = normalized['metadata']['startTime']
        
        if 'flightModeChanges' in normalized:
            context['flight_modes'] = [mode[1] for mode in normalized['flightModeChanges'] if isinstance(mode, (list, tuple)) and len(mode) > 1]
            context['total_events'] = len(normalized['flightModeChanges'])
        
        if 'trajectories' in normalized:
            for trajectory_name, trajectory_data in normalized['trajectories'].items():
                if 'trajectory' in trajectory_data:
                    context['gps_points'] = len(trajectory_data['trajectory'])
                    
                    # Calculate altitude and speed ranges
                    altitudes = [point[2] for point in trajectory_data['trajectory'] if isinstance(point, (list, tuple)) and len(point) > 2]
                    if altitudes:
                        context['altitude_range'] = {
                            'min': min(altitudes),
                            'max': max(altitudes),
                            'units': 'meters'
                        }
                    break
        
        self.update_session_activity(session_id)
        logger.info(f"Stored flight data for session {session_id}")
        return True

    def _normalize_flight_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Best-effort normalization of frontend payload to structures expected by backend.

        - params: ensure dict of {name: value}
        - events: ensure list of dicts with at least {timestamp, type, message}
        - attitude_series: derive from timeAttitude if present
        - rc_inputs: pass-through if present, else omit
        """
        try:
            normalized = dict(data) if isinstance(data, dict) else {}

            # Normalize params
            params_obj = normalized.get('params')
            if isinstance(params_obj, dict):
                pass
            elif isinstance(params_obj, list):
                # Expect list of [timestamp, name, value]
                params_dict = {}
                for entry in params_obj:
                    if isinstance(entry, (list, tuple)) and len(entry) >= 3:
                        _, name, value = entry[0], entry[1], entry[2]
                        if isinstance(name, str):
                            params_dict[name] = value
                normalized['params'] = params_dict
            else:
                # Unknown shape (e.g., ParamSeeker-like); try to snapshot to dict via common attributes
                params_dict = {}
                try:
                    # If it's a mapping-like
                    for k in getattr(params_obj, 'keys', lambda: [])():
                        params_dict[k] = params_obj[k]
                except Exception:
                    pass
                normalized['params'] = params_dict

            # Normalize events: list of dicts
            events = normalized.get('events')
            if isinstance(events, list):
                new_events = []
                for ev in events:
                    if isinstance(ev, dict):
                        new_events.append(ev)
                    elif isinstance(ev, (list, tuple)) and len(ev) >= 2:
                        ts, label = ev[0], ev[1]
                        new_events.append({
                            'timestamp': float(ts) if isinstance(ts, (int, float)) else 0,
                            'type': str(label),
                            'message': str(label),
                            'severity': 'info'
                        })
                normalized['events'] = new_events

            # Build attitude_series from timeAttitude (map of timestamp -> [r,p,y])
            if 'attitude_series' not in normalized:
                time_att = normalized.get('timeAttitude')
                if isinstance(time_att, dict):
                    series = []
                    for ts_str, angles in time_att.items():
                        try:
                            ts = float(ts_str)
                        except Exception:
                            ts = float(angles[3]) if isinstance(angles, (list, tuple)) and len(angles) > 3 and isinstance(angles[3], (int, float)) else 0.0
                        if isinstance(angles, (list, tuple)) and len(angles) >= 3:
                            series.append({
                                'timestamp': ts,
                                'roll': angles[0],
                                'pitch': angles[1],
                                'yaw': angles[2]
                            })
                    if series:
                        normalized['attitude_series'] = series

            return normalized
        except Exception as e:
            logger.warning(f"Flight data normalization failed: {e}")
            return data
    
    def get_flight_data_summary(self, session_id: str) -> Dict[str, Any]:
        """Get a summary of flight data for the session"""
        if session_id not in self.sessions:
            return {}
        
        return self.sessions[session_id]['context']
    
    def get_available_data_types(self, session_id: str) -> List[str]:
        """Get list of available data types in the flight data"""
        if session_id not in self.flight_data:
            return []
        
        flight_data = self.flight_data[session_id]
        available_types = []
        
        # Check for common data types
        data_checks = {
            'GPS Data': 'trajectories' in flight_data,
            'Flight Modes': 'flightModeChanges' in flight_data and len(flight_data['flightModeChanges']) > 0,
            'Events': 'events' in flight_data and len(flight_data['events']) > 0,
            'Mission Data': 'mission' in flight_data and len(flight_data['mission']) > 0,
            'Parameters': 'params' in flight_data,
            'Attitude Data': 'timeAttitude' in flight_data,
            'Vehicle Info': 'vehicle' in flight_data,
            'Metadata': 'metadata' in flight_data
        }
        
        for data_type, is_available in data_checks.items():
            if is_available:
                available_types.append(data_type)
        
        return available_types
    
    def get_or_create_llm_agent(self, session_id: str) -> Any:
        """Get or create an LLM agent for the session"""
        if session_id not in self.llm_agents:
            try:
                # Create a new LLM agent for this session
                self.llm_agents[session_id] = LangGraphReactAgent(session_id=session_id)
                logger.info(f"Created LLM agent for session {session_id}")
            except Exception as e:
                logger.error(f"Failed to create LLM agent for session {session_id}: {str(e)}")
                return None
        
        # Ensure telemetry cache is synchronized for this session
        try:
            if session_id in self.flight_data:
                telemetry_retriever = get_global_telemetry_retriever()
                telemetry_retriever.set_flight_data(session_id, self.flight_data[session_id])
        except Exception as e:
            logger.warning(f"Failed to sync telemetry cache for session {session_id}: {e}")
        
        return self.llm_agents[session_id]
    
    def add_flight_data_to_rag(self, session_id: str, flight_data: Dict[str, Any]) -> str:
        """Add flight data to the RAG system and telemetry retriever for the session"""
        try:
            # Use the global RAG manager
            rag_manager = get_global_rag_manager()
            # Format flight data as text
            from text_utils import format_flight_data_text
            flight_data_text = format_flight_data_text(flight_data)
            documents = [flight_data_text]
            metadata_list = [{
                'type': 'overview',
                'session_id': session_id
            }]

            # Local export disabled
            # try:
            #     self._export_rag_documents(session_id, documents, metadata_list)
            # except Exception as exp_err:
            #     logger.warning(f"RAG local export failed for session {session_id}: {exp_err}")

            result = rag_manager.add_documents(session_id, documents, metadata_list=metadata_list)
            
            # Also add to telemetry retriever for dynamic queries
            telemetry_retriever = get_global_telemetry_retriever()
            telemetry_retriever.set_flight_data(session_id, flight_data)
            
            logger.info(f"Added flight data to RAG and telemetry retriever for session {session_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to add flight data to RAG for session {session_id}: {str(e)}")
            return f"Error adding flight data to RAG: {str(e)}"

    def _export_rag_documents(self, session_id: str, documents: List[str], metadata_list: List[Dict[str, Any]]):
        """Local RAG export disabled (rag_exports no-op)."""
        return
    
    def _format_flight_data_for_rag(self, flight_data: Dict[str, Any]) -> str:
        """Format flight data as text for RAG ingestion"""
        formatted_text = "Flight Data Summary:\n"
        
        # Add vehicle information
        if 'vehicle' in flight_data:
            formatted_text += f"Vehicle Type: {flight_data['vehicle']}\n"
        
        # Add metadata
        if 'metadata' in flight_data and flight_data['metadata']:
            metadata = flight_data['metadata']
            if 'startTime' in metadata:
                formatted_text += f"Flight Start Time: {metadata['startTime']}\n"
        
        # Add flight modes
        if 'flightModeChanges' in flight_data:
            modes = [mode[1] for mode in flight_data['flightModeChanges']]
            unique_modes = list(set(modes))
            formatted_text += f"Flight Modes Used: {', '.join(unique_modes)}\n"
            formatted_text += f"Total Mode Changes: {len(flight_data['flightModeChanges'])}\n"
        
        # Add trajectory information
        if 'trajectories' in flight_data:
            for trajectory_name, trajectory_data in flight_data['trajectories'].items():
                if 'trajectory' in trajectory_data:
                    trajectory = trajectory_data['trajectory']
                    formatted_text += f"GPS Trajectory Points: {len(trajectory)}\n"
                    
                    # Add altitude range if available
                    altitudes = [point[2] for point in trajectory if len(point) > 2]
                    if altitudes:
                        formatted_text += f"Altitude Range: {min(altitudes):.1f}m to {max(altitudes):.1f}m\n"
                    break
        
        # Add events
        if 'events' in flight_data:
            formatted_text += f"Total Events: {len(flight_data['events'])}\n"
        
        # Add mission data
        if 'mission' in flight_data:
            formatted_text += f"Mission Commands: {len(flight_data['mission'])}\n"
        
        # Add parameters
        if 'params' in flight_data:
            formatted_text += f"Vehicle Parameters: {len(flight_data['params'])} parameters available\n"
        
        return formatted_text

# Initialize session manager
session_manager = SessionManager()

@app.route('/api/chat', methods=['POST'])
def chat():
    """Main chat endpoint"""
    try:
        data = request.get_json()
        session_id = request.headers.get('X-Session-ID')
        message = data.get('message', '').strip()
        
        if not session_id:
            return jsonify({'error': 'Session ID required'}), 400
        
        if not message:
            return jsonify({'error': 'Message required'}), 400
        
        # Get or create session
        session = session_manager.get_session(session_id)
        if not session:
            session_manager.create_session(session_id)
            session = session_manager.get_session(session_id)
        
        # Add user message
        session_manager.add_message(session_id, message, 'user')
        
        # Generate response based on available data
        response = generate_chat_response(session_id, message)
        
        # Add bot response
        session_manager.add_message(session_id, response, 'bot')
        
        return jsonify({
            'message': response,
            'session_id': session_id,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/flight-data', methods=['POST'])
def store_flight_data():
    """Store flight data for a session"""
    try:
        data = request.get_json()
        session_id = request.headers.get('X-Session-ID')
        
        if not session_id:
            return jsonify({'error': 'Session ID required'}), 400
        
        if not data:
            return jsonify({'error': 'Flight data required'}), 400
        
        # Create session if it doesn't exist
        if not session_manager.get_session(session_id):
            session_manager.create_session(session_id)
        
        # Store flight data
        success = session_manager.store_flight_data(session_id, data)
        
        if success:
            # Add flight data to RAG for AI analysis
            rag_result = session_manager.add_flight_data_to_rag(session_id, data)
            logger.info(f"RAG result for session {session_id}: {rag_result}")
            
            summary = session_manager.get_flight_data_summary(session_id)
            available_types = session_manager.get_available_data_types(session_id)
            
            return jsonify({
                'success': True,
                'session_id': session_id,
                'data_summary': summary,
                'available_data_types': available_types,
                'rag_status': rag_result,
                'message': 'Flight data stored successfully'
            })
        else:
            return jsonify({'error': 'Failed to store flight data'}), 500
            
    except Exception as e:
        logger.error(f"Flight data storage error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/session/<session_id>', methods=['GET'])
def get_session_info(session_id):
    """Get session information and available data"""
    try:
        session = session_manager.get_session(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        summary = session_manager.get_flight_data_summary(session_id)
        available_types = session_manager.get_available_data_types(session_id)
        
        return jsonify({
            'session_id': session_id,
            'created_at': session['created_at'],
            'last_activity': session['last_activity'],
            'message_count': len(session['messages']),
            'data_summary': summary,
            'available_data_types': available_types,
            'has_flight_data': summary.get('has_flight_data', False)
        })
        
    except Exception as e:
        logger.error(f"Session info error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/sessions', methods=['GET'])
def list_sessions():
    """List all active sessions"""
    try:
        sessions_list = []
        for session_id, session_data in session_manager.sessions.items():
            summary = session_manager.get_flight_data_summary(session_id)
            sessions_list.append({
                'session_id': session_id,
                'created_at': session_data['created_at'],
                'last_activity': session_data['last_activity'],
                'message_count': len(session_data['messages']),
                'has_flight_data': summary.get('has_flight_data', False),
                'vehicle_type': summary.get('vehicle_type'),
                'flight_modes_count': len(summary.get('flight_modes', []))
            })
        
        return jsonify({
            'sessions': sessions_list,
            'total_sessions': len(sessions_list)
        })
        
    except Exception as e:
        logger.error(f"Sessions list error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'active_sessions': len(session_manager.sessions),
        'cached_flight_data': len(session_manager.flight_data),
        'llm_agent_available': llm_agent is not None
    })

@app.route('/api/prompt/<session_id>', methods=['POST'])
def update_system_prompt(session_id):
    """Update the system prompt for a session"""
    try:
        data = request.get_json()
        prompt_name = data.get('prompt_name', 'ardupilot_analyst')
        
        # Get or create LLM agent for this session
        agent = session_manager.get_or_create_llm_agent(session_id)
        if not agent:
            return jsonify({'error': 'Failed to create LLM agent'}), 500
        
        # Update the system prompt
        result = agent.update_system_prompt(prompt_name)
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'prompt_name': prompt_name,
            'message': result
        })
        
    except Exception as e:
        logger.error(f"Prompt update error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/prompts', methods=['GET'])
def list_available_prompts():
    """List all available system prompts"""
    try:
        from prompts import list_available_prompts as get_prompts
        prompts = get_prompts()
        
        return jsonify({
            'available_prompts': prompts,
            'total_prompts': len(prompts)
        })
        
    except Exception as e:
        logger.error(f"Prompts list error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/rag/collections', methods=['GET'])
def list_rag_collections():
    """List all RAG collections"""
    try:
        rag_manager = get_global_rag_manager()
        collections = rag_manager.list_collections(limit=50)
        
        return jsonify({
            'collections': collections,
            'total_collections': len(collections)
        })
        
    except Exception as e:
        logger.error(f"RAG collections list error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/rag/collections/<session_id>', methods=['GET'])
def get_rag_collection_status(session_id):
    """Get RAG collection status for a session"""
    try:
        rag_manager = get_global_rag_manager()
        status = rag_manager.get_collection_status(session_id)
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"RAG collection status error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/rag/collections/<session_id>', methods=['DELETE'])
def delete_rag_collection(session_id):
    """Delete RAG collection for a session"""
    try:
        rag_manager = get_global_rag_manager()
        result = rag_manager.delete_collection(session_id)
        
        return jsonify({
            'success': True,
            'message': result
        })
        
    except Exception as e:
        logger.error(f"RAG collection deletion error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/rag/collections/<session_id>/clear', methods=['POST'])
def clear_rag_collection(session_id):
    """Clear RAG collection for a session"""
    try:
        rag_manager = get_global_rag_manager()
        result = rag_manager.clear_collection(session_id)
        
        return jsonify({
            'success': True,
            'message': result
        })
        
    except Exception as e:
        logger.error(f"RAG collection clear error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/rag/stats', methods=['GET'])
def get_rag_system_stats():
    """Get RAG system statistics"""
    try:
        rag_manager = get_global_rag_manager()
        stats = rag_manager.get_manager_stats()
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"RAG system stats error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/rag/cleanup', methods=['POST'])
def cleanup_rag_collections():
    """Manually trigger cleanup of old RAG collections"""
    try:
        rag_manager = get_global_rag_manager()
        result = rag_manager.cleanup_old_collections()
        
        return jsonify({
            'success': True,
            'message': result
        })
        
    except Exception as e:
        logger.error(f"RAG cleanup error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# Agentic conversation endpoints
@app.route('/api/conversation/<session_id>/state', methods=['GET'])
def get_conversation_state(session_id):
    """Get conversation state for a session"""
    try:
        conversation_manager = get_global_conversation_manager()
        summary = conversation_manager.get_conversation_summary(session_id)
        
        return jsonify(summary)
        
    except Exception as e:
        logger.error(f"Conversation state error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/telemetry/<session_id>/summary', methods=['GET'])
def get_telemetry_summary(session_id):
    """Get telemetry data summary for a session"""
    try:
        telemetry_retriever = get_global_telemetry_retriever()
        summary = telemetry_retriever.get_telemetry_summary(session_id)
        
        return jsonify(summary)
        
    except Exception as e:
        logger.error(f"Telemetry summary error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/telemetry/<session_id>/query', methods=['POST'])
def query_telemetry_data(session_id):
    """Query specific telemetry data"""
    try:
        data = request.get_json()
        parameter = data.get('parameter')
        time_range = data.get('time_range')
        aggregation = data.get('aggregation', 'raw')
        
        if not parameter:
            return jsonify({'error': 'Parameter is required'}), 400
        
        telemetry_retriever = get_global_telemetry_retriever()
        from telemetry_retriever import TelemetryQuery
        
        # Parse time range if provided
        time_range_tuple = None
        if time_range and isinstance(time_range, list) and len(time_range) == 2:
            time_range_tuple = (float(time_range[0]), float(time_range[1]))
        
        query = TelemetryQuery(
            parameter=parameter,
            time_range=time_range_tuple,
            aggregation=aggregation
        )
        
        result = telemetry_retriever.query_telemetry(session_id, query)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Telemetry query error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Anomaly detection endpoints
@app.route('/api/anomaly/<session_id>/analyze', methods=['POST'])
def analyze_flight_anomalies(session_id):
    """Analyze flight data for anomalies"""
    try:
        data = request.get_json()
        user_question = data.get('question', '') if data else ''
        
        telemetry_retriever = get_global_telemetry_retriever()
        analysis_result = telemetry_retriever.analyze_flight_anomalies(session_id, user_question)
        
        return jsonify(analysis_result)
        
    except Exception as e:
        logger.error(f"Anomaly analysis error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/anomaly/<session_id>/structured-data', methods=['GET'])
def get_structured_flight_data(session_id):
    """Get structured flight data for analysis"""
    try:
        telemetry_retriever = get_global_telemetry_retriever()
        structured_data = telemetry_retriever.get_structured_telemetry_data(session_id)
        
        return jsonify(structured_data)
        
    except Exception as e:
        logger.error(f"Structured data error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/investigate/<session_id>', methods=['POST'])
def investigate_flight_data(session_id):
    """Comprehensive investigative analysis endpoint for high-level questions"""
    try:
        data = request.get_json()
        user_question = data.get('question', '') if data else ''
        
        if not user_question:
            return jsonify({'error': 'Question is required'}), 400
        
        # Get session context
        session = session_manager.get_session(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        context = session_manager.get_flight_data_summary(session_id)
        if not context.get('has_flight_data', False):
            return jsonify({'error': 'No flight data available for analysis'}), 400
        
        # Perform comprehensive analysis
        telemetry_retriever = get_global_telemetry_retriever()
        
        # Get anomaly analysis
        analysis_result = telemetry_retriever.analyze_flight_anomalies(session_id, user_question)
        
        # Get structured data
        structured_data = telemetry_retriever.get_structured_telemetry_data(session_id)
        
        # Get available parameters
        available_params = telemetry_retriever._get_available_parameters(
            telemetry_retriever.get_flight_data(session_id)
        )
        
        # Create comprehensive response
        response = {
            'session_id': session_id,
            'user_question': user_question,
            'analysis_timestamp': datetime.now().isoformat(),
            'flight_context': context,
            'available_parameters': available_params,
            'anomaly_analysis': analysis_result,
            'structured_data': structured_data,
            'data_completeness': {
                'total_parameters_available': len(available_params),
                'has_gps_data': 'GPS' in available_params,
                'has_battery_data': any('BAT' in param for param in available_params),
                'has_rc_data': any('RC' in param for param in available_params),
                'has_flight_modes': 'MODE' in available_params,
                'has_events': 'EVENTS' in available_params
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Investigation error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/data-completeness/<session_id>', methods=['GET'])
def get_data_completeness(session_id):
    """Get comprehensive data completeness report for a session"""
    try:
        telemetry_retriever = get_global_telemetry_retriever()
        flight_data = telemetry_retriever.get_flight_data(session_id)
        
        if not flight_data:
            return jsonify({'error': 'No flight data available'}), 404
        
        # Get available parameters
        available_params = telemetry_retriever._get_available_parameters(flight_data)
        
        # Analyze data completeness
        completeness_report = {
            'session_id': session_id,
            'total_parameters': len(available_params),
            'data_sources': {},
            'parameter_categories': {
                'gps': [p for p in available_params if 'GPS' in p],
                'battery': [p for p in available_params if 'BAT' in p or 'VOLTAGE' in p],
                'rc_control': [p for p in available_params if 'RC' in p or 'RSSI' in p],
                'flight_modes': [p for p in available_params if 'MODE' in p],
                'events': [p for p in available_params if 'EVENT' in p],
                'parameters': [p for p in available_params if p in flight_data.get('params', {})],
                'mission': [p for p in available_params if 'MISSION' in p or 'WAYPOINT' in p]
            },
            'data_quality_indicators': {
                'has_trajectory_data': 'trajectories' in flight_data,
                'has_gps_metadata': 'gps_metadata' in flight_data,
                'has_flight_modes': 'flightModeChanges' in flight_data,
                'has_events': 'events' in flight_data,
                'has_parameters': 'params' in flight_data,
                'has_mission_data': 'mission' in flight_data,
                'has_rc_data': 'rc_inputs' in flight_data
            }
        }
        
        # Count data points in each source
        if 'trajectories' in flight_data:
            total_trajectory_points = sum(
                len(traj_data.get('trajectory', [])) 
                for traj_data in flight_data['trajectories'].values()
            )
            completeness_report['data_sources']['trajectories'] = {
                'count': len(flight_data['trajectories']),
                'total_points': total_trajectory_points
            }
        
        if 'events' in flight_data:
            completeness_report['data_sources']['events'] = {
                'count': len(flight_data['events'])
            }
        
        if 'flightModeChanges' in flight_data:
            completeness_report['data_sources']['flight_modes'] = {
                'count': len(flight_data['flightModeChanges'])
            }
        
        if 'params' in flight_data:
            completeness_report['data_sources']['parameters'] = {
                'count': len(flight_data['params'])
            }
        
        return jsonify(completeness_report)
        
    except Exception as e:
        logger.error(f"Data completeness error: {str(e)}")
        return jsonify({'error': str(e)}), 500

def generate_chat_response(session_id: str, user_message: str) -> str:
    """Generate a response using the new three-layer pipeline with safe fallback."""
    session = session_manager.get_session(session_id)
    if not session:
        return "I'm sorry, I couldn't find your session. Please try again."
    
    # Get or create LLM agent for this session
    agent = session_manager.get_or_create_llm_agent(session_id)
    if not agent:
        return "I'm sorry, I'm having trouble connecting to the AI service. Please try again later."
    
    try:
        # Prefer three-layer pipeline always
        response = agent.generate_multilayer(user_message)
        if response and isinstance(response, str) and response.strip():
            return response
        # If multi-layer returns empty, fall back
        raise RuntimeError("Empty multilayer response")
        
    except Exception as e:
        logger.error(f"Error generating chat response for session {session_id}: {str(e)}")
        # Safe fallback to minimal guidance without leaking details
        return "I couldn't complete the analysis. Please try rephrasing your question or ensure a flight log is loaded."


if __name__ == '__main__':
    # Initialize LLM agent on startup
    initialize_llm_agent()
    app.run(host='0.0.0.0', port=8000, debug=True)
