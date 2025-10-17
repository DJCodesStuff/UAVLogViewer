from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import os
import json
from config import Config
from session_manager import SessionManager
from telemetry_service import TelemetryService
from gemini_service import GeminiService
from qdrant_service import QdrantService
from agent import FlightAnalysisAgent
from ingestion_agent import DataIngestionAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Validate configuration
try:
    Config.validate()
except ValueError as e:
    logger.error(f"Configuration error: {e}")
    logger.error("Please set GOOGLE_API_KEY in your .env file")
    exit(1)

# Initialize services
session_manager = SessionManager()
telemetry_service = TelemetryService(session_manager)
gemini_service = GeminiService(Config.GOOGLE_API_KEY, Config.GEMINI_MODEL)
qdrant_service = QdrantService(Config.QDRANT_URL, Config.QDRANT_API_KEY)

# Initialize agent
agent = FlightAnalysisAgent(
    gemini_service=gemini_service,
    telemetry_service=telemetry_service,
    qdrant_service=qdrant_service
)

# Ingestion agent for structured docs
ingestion_agent = DataIngestionAgent(
    gemini_service=gemini_service,
    qdrant_service=qdrant_service,
    telemetry_service=telemetry_service
)

logger.info("UAV Log Viewer Backend API started")
logger.info(f"Qdrant available: {qdrant_service.is_available()}")


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'qdrant_available': qdrant_service.is_available()
    }), 200


@app.route('/api/flight-data', methods=['POST'])
def upload_flight_data():
    """Receive and store flight data from frontend"""
    try:
        data = request.get_json()
        session_id = request.headers.get('X-Session-ID')
        
        if not session_id:
            return jsonify({'error': 'Session ID required'}), 400
        
        # Store flight data
        summary = session_manager.store_flight_data(session_id, data)
        
        logger.info(f"Received flight data for session {session_id}")
        logger.info(f"Available parameters: {summary.available_parameters}")

        # Index per-session telemetry into Qdrant (per-session collection)
        try:
            session_collection = f"session_{session_id}"
            # Ensure collection exists
            qdrant_service.ensure_collection(session_collection)
            # Build text chunks
            texts, payloads = telemetry_service.create_vector_documents(session_id, data)

            # Dump RAG chunks to rag_docs for inspection
            # try:
            #     project_root = os.path.dirname(os.path.dirname(__file__))
            #     dump_dir = os.path.join(project_root, 'rag_docs', f'session_{session_id}')
            #     os.makedirs(dump_dir, exist_ok=True)

            #     # Write each text chunk to a file with type label
            #     for idx, (text, pl) in enumerate(zip(texts, payloads)):
            #         chunk_type = (pl.get('type') or 'chunk') if isinstance(pl, dict) else 'chunk'
            #         fname = f"{idx:03d}_{chunk_type}.txt"
            #         with open(os.path.join(dump_dir, fname), 'w', encoding='utf-8') as f:
            #             f.write(text if isinstance(text, str) else str(text))

            #     # Write manifest with payload metadata
            #     manifest_path = os.path.join(dump_dir, 'manifest.json')
            #     with open(manifest_path, 'w', encoding='utf-8') as mf:
            #         json.dump({
            #             'session_id': session_id,
            #             'count': len(texts),
            #             'payloads': payloads
            #         }, mf, ensure_ascii=False, indent=2)
            # except Exception as e:
            #     logger.error(f"Error writing RAG debug dump: {e}")
            # Generate embeddings
            vectors = gemini_service.embed_texts(texts)
            if texts and vectors and len(texts) == len(vectors):
                qdrant_service.add_documents_to_collection(session_collection, [
                    {**pl, 'session_id': session_id}
                for pl in payloads], vectors)
                logger.info(f"Indexed {len(texts)} telemetry chunks into {session_collection}")
            else:
                logger.warning("Skipping Qdrant upsert: missing embeddings or mismatch counts")
        except Exception as e:
            logger.error(f"Error indexing session telemetry to Qdrant: {e}")

        # Also index structured, LLM-friendly docs via ingestion agent
        try:
            _ = ingestion_agent.ingest_session(session_id, data)
        except Exception as e:
            logger.error(f"Error ingesting structured docs: {e}")
        
        return jsonify({
            'status': 'success',
            'session_id': session_id,
            'vehicle_type': summary.vehicle_type,
            'log_type': summary.log_type,
            'available_data_types': summary.available_parameters,
            'data_points': summary.data_points,
            'has_gps': summary.has_gps,
            'has_battery': summary.has_battery,
            'has_attitude': summary.has_attitude
        }), 200
    
    except Exception as e:
        logger.error(f"Error uploading flight data: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat', methods=['POST'])
def chat():
    """Main chat endpoint - processes user messages"""
    try:
        data = request.get_json()
        session_id = request.headers.get('X-Session-ID') or data.get('sessionId')
        user_message = data.get('message')
        
        if not session_id or not user_message:
            return jsonify({'error': 'Session ID and message required'}), 400
        
        # Get session
        session = session_manager.get_or_create_session(session_id)
        
        # Add user message to history
        session_manager.add_message(session_id, 'user', user_message)
        
        logger.info(f"Chat message from {session_id}: {user_message}")
        
        # Always run the agent. The agent will use RAG if no in-memory telemetry is present
        response_message = agent.run(
            question=user_message,
            session_id=session_id,
            max_iterations=Config.MAX_AGENT_ITERATIONS
        )
        
        # Add assistant message to history
        session_manager.add_message(session_id, 'assistant', response_message)
        
        return jsonify({
            'message': response_message,
            'session_id': session_id,
            'timestamp': data.get('timestamp')
        }), 200
    
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        return jsonify({
            'message': 'I apologize, but I encountered an error processing your request.',
            'error': str(e)
        }), 500


@app.route('/api/session/<session_id>/summary', methods=['GET'])
def get_session_summary(session_id):
    """Get summary of session data"""
    try:
        session = session_manager.get_session(session_id)
        
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        summary = session_manager._create_flight_summary(session_id, session.flight_data)
        
        return jsonify({
            'session_id': session_id,
            'vehicle_type': summary.vehicle_type,
            'log_type': summary.log_type,
            'available_parameters': summary.available_parameters,
            'has_gps': summary.has_gps,
            'has_battery': summary.has_battery,
            'has_attitude': summary.has_attitude,
            'data_points': summary.data_points,
            'conversation_length': len(session.conversation_history)
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting session summary: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/session/<session_id>/reset', methods=['POST'])
def reset_session(session_id):
    """Reset session conversation history"""
    try:
        session = session_manager.get_session(session_id)
        
        if session:
            session.conversation_history.clear()
            logger.info(f"Reset conversation for session {session_id}")
            return jsonify({'status': 'success'}), 200
        else:
            return jsonify({'error': 'Session not found'}), 404
    
    except Exception as e:
        logger.error(f"Error resetting session: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/telemetry/<session_id>/<parameter>', methods=['GET'])
def get_telemetry(session_id, parameter):
    """Get specific telemetry parameter"""
    try:
        data = telemetry_service.get_parameter_data(session_id, parameter)
        return jsonify(data), 200
    except Exception as e:
        logger.error(f"Error getting telemetry: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/anomalies/<session_id>', methods=['GET'])
def get_anomalies(session_id):
    """Get detected anomalies"""
    try:
        anomalies = telemetry_service.detect_anomalies(session_id)
        return jsonify({
            'session_id': session_id,
            'anomalies': anomalies,
            'count': len(anomalies)
        }), 200
    except Exception as e:
        logger.error(f"Error detecting anomalies: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/debug/sessions', methods=['GET'])
def debug_sessions():
    """Debug endpoint to check all sessions"""
    try:
        sessions_info = {}
        for session_id, session in session_manager.sessions.items():
            sessions_info[session_id] = {
                'has_flight_data': bool(session.flight_data),
                'data_fields': len(session.flight_data) if session.flight_data else 0,
                'conversation_length': len(session.conversation_history),
                'created_at': session.created_at,
                'last_activity': session.last_activity
            }
        
        return jsonify({
            'total_sessions': len(session_manager.sessions),
            'sessions': sessions_info
        }), 200
    except Exception as e:
        logger.error(f"Error in debug endpoint: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG
    )

