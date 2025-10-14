from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
import time
from datetime import datetime
import json
from typing import Dict, List, Any
import logging
from llm_config import LangGraphReactAgent

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
        
        # Store the flight data
        self.flight_data[session_id] = flight_data
        self.sessions[session_id]['flight_data'] = flight_data
        
        # Update context with flight data summary
        context = self.sessions[session_id]['context']
        context['has_flight_data'] = True
        
        # Extract key information from flight data
        if 'vehicle' in flight_data:
            context['vehicle_type'] = flight_data['vehicle']
        
        if 'metadata' in flight_data and flight_data['metadata']:
            if 'startTime' in flight_data['metadata']:
                context['start_time'] = flight_data['metadata']['startTime']
        
        if 'flightModeChanges' in flight_data:
            context['flight_modes'] = [mode[1] for mode in flight_data['flightModeChanges']]
            context['total_events'] = len(flight_data['flightModeChanges'])
        
        if 'trajectories' in flight_data:
            for trajectory_name, trajectory_data in flight_data['trajectories'].items():
                if 'trajectory' in trajectory_data:
                    context['gps_points'] = len(trajectory_data['trajectory'])
                    
                    # Calculate altitude and speed ranges
                    altitudes = [point[2] for point in trajectory_data['trajectory'] if len(point) > 2]
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
        
        return self.llm_agents[session_id]
    
    def add_flight_data_to_rag(self, session_id: str, flight_data: Dict[str, Any]) -> str:
        """Add flight data to the RAG system for the session"""
        agent = self.get_or_create_llm_agent(session_id)
        if not agent:
            return "Failed to create LLM agent for RAG"
        
        try:
            # Convert flight data to text format for RAG
            flight_data_text = self._format_flight_data_for_rag(flight_data)
            result = agent.add_rag_documents([flight_data_text])
            logger.info(f"Added flight data to RAG for session {session_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to add flight data to RAG for session {session_id}: {str(e)}")
            return f"Error adding flight data to RAG: {str(e)}"
    
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

def generate_chat_response(session_id: str, user_message: str) -> str:
    """Generate a dynamic response using the LLM agent"""
    session = session_manager.get_session(session_id)
    if not session:
        return "I'm sorry, I couldn't find your session. Please try again."
    
    # Get or create LLM agent for this session
    agent = session_manager.get_or_create_llm_agent(session_id)
    if not agent:
        return "I'm sorry, I'm having trouble connecting to the AI service. Please try again later."
    
    try:
        # Get session context for better responses
        context = session_manager.get_flight_data_summary(session_id)
        available_types = session_manager.get_available_data_types(session_id)
        
        # Build context-aware prompt
        context_info = ""
        if context.get('has_flight_data', False):
            context_info = f"""
Flight Data Context:
- Vehicle Type: {context.get('vehicle_type', 'Unknown')}
- Available Data Types: {', '.join(available_types)}
- GPS Points: {context.get('gps_points', 0)}
- Flight Modes: {', '.join(context.get('flight_modes', []))}
- Total Events: {context.get('total_events', 0)}
"""
            if context.get('altitude_range'):
                alt_range = context['altitude_range']
                context_info += f"- Altitude Range: {alt_range['min']:.1f}m to {alt_range['max']:.1f}m\n"
        else:
            context_info = "No flight data has been uploaded yet. Please upload a log file first."
        
        # Create enhanced prompt with context
        enhanced_prompt = f"""
{context_info}

User Question: {user_message}

Please provide a helpful and detailed response about the flight data or UAV analysis. If flight data is available, use it to provide specific insights. If no flight data is available, explain what the user needs to do to get started.
"""
        
        # Generate response using the LLM agent
        response = agent.generate(enhanced_prompt)
        
        # Fallback to basic response if LLM fails
        if not response or response.strip() == "":
            if context.get('has_flight_data', False):
                return f"I can help you analyze your flight data. You have {', '.join(available_types)} available. What specific aspect would you like to know more about?"
            else:
                return "Hello! I'm your UAV Log Viewer assistant. Please upload a flight log file first, and then I'll be able to help you with detailed analysis!"
        
        return response
        
    except Exception as e:
        logger.error(f"Error generating chat response for session {session_id}: {str(e)}")
        
        # Fallback response
        if context.get('has_flight_data', False):
            return f"I can help you analyze your flight data. You have {', '.join(available_types)} available. What specific aspect would you like to know more about?"
        else:
            return "Hello! I'm your UAV Log Viewer assistant. Please upload a flight log file first, and then I'll be able to help you with detailed analysis!"

if __name__ == '__main__':
    # Initialize LLM agent on startup
    initialize_llm_agent()
    app.run(host='0.0.0.0', port=8000, debug=True)
