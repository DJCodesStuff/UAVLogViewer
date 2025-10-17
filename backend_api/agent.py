from typing import Dict, Any, List, TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
import logging

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """State for the flight analysis agent"""
    question: str
    session_id: str
    thought: str
    action: str
    observation: str
    answer: str
    iteration: int
    max_iterations: int
    should_continue: bool


class FlightAnalysisAgent:
    """Simple React-style agent for flight data analysis"""
    
    def __init__(self, gemini_service, telemetry_service, qdrant_service):
        self.gemini = gemini_service
        self.telemetry = telemetry_service
        self.qdrant = qdrant_service
        self.graph = self._create_graph()
    
    def _create_graph(self):
        """Create the agent workflow graph"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("think", self._think_node)
        workflow.add_node("act", self._act_node)
        workflow.add_node("respond", self._respond_node)
        
        # Add edges
        workflow.set_entry_point("think")
        workflow.add_edge("think", "act")
        workflow.add_conditional_edges(
            "act",
            self._should_continue,
            {
                "continue": "think",
                "end": "respond"
            }
        )
        workflow.add_edge("respond", END)
        
        return workflow.compile()
    
    def _think_node(self, state: AgentState) -> AgentState:
        """Agent reasoning step - more intelligent and proactive"""
        question = state['question']
        observation = state.get('observation', '')
        session_id = state['session_id']
        iteration = state.get('iteration', 0)
        
        # Always use RAG. Do not depend on in-memory telemetry.
        state['action'] = 'rag_answer'
        state['iteration'] = iteration + 1
        state['should_continue'] = False  # single-step RAG answer
        return state
        
        # Get conversation history for context
        conversation_history = self.telemetry.session_manager.get_conversation_history(session_id, limit=5)
        conversation_context = ""
        if conversation_history:
            recent_messages = conversation_history[-3:]  # Last 3 messages
            conversation_context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in recent_messages])
        
        # Determine what action to take with more intelligent reasoning
        prompt = f"""You are an intelligent flight data analyst agent. You maintain conversation state and proactively ask for clarifications.

CONVERSATION CONTEXT:
{conversation_context}

CURRENT QUESTION: {question}

AVAILABLE DATA IN THIS SESSION:
- Vehicle: {available_data.get('vehicle_type', 'Unknown')}
- Log type: {available_data.get('log_type', 'Unknown')}
- Available parameters: {', '.join(available_data.get('available_parameters', []))}
- Has GPS: {available_data.get('has_gps', False)}
- Has Battery: {available_data.get('has_battery', False)}
- Has Attitude: {available_data.get('has_attitude', False)}
- Has Events: {available_data.get('has_events', False)}
- Data points: {available_data.get('data_points', 0)}

PREVIOUS OBSERVATION: {observation}
ITERATION: {iteration}

ANALYSIS STRATEGY:
1. If this is the first iteration and the question is ambiguous, ask for clarification
2. If the question is clear, retrieve the most relevant data first
3. If you need multiple data sources, prioritize the most important one
4. If you have enough data to answer, proceed to answer

AVAILABLE ACTIONS:
- "retrieve_gps" - Get GPS/position data (for location, altitude, speed questions)
- "retrieve_battery" - Get battery data (for power, temperature, voltage questions)  
- "retrieve_altitude" - Get altitude data (for height, climb, descent questions)
- "retrieve_attitude" - Get attitude data (for orientation, roll, pitch, yaw questions)
- "retrieve_events" - Get flight events (for errors, warnings, mode changes)
- "detect_anomalies" - Detect anomalies (for safety, issues, problems questions)
- "ask_clarification" - Ask user for clarification (if question is ambiguous)
- "answer" - Provide final answer (when you have sufficient data)

DECISION LOGIC:
- For altitude questions: choose "retrieve_altitude" if has_gps=True
- For battery questions: choose "retrieve_battery" if has_battery=True  
- For error/problem questions: choose "retrieve_events" or "detect_anomalies"
- For ambiguous questions: choose "ask_clarification"
- For complex questions needing multiple data: start with most relevant action

Respond with ONLY the action name (no explanation)."""
        
        action = self.gemini.chat(prompt, system_prompt="You are an intelligent flight data analyst. Be decisive and choose the most appropriate action.")
        action = action.strip().lower()
        
        # Check if this is a complex question that needs special handling
        question_lower = question.lower()
        if any(word in question_lower for word in ['anomalies', 'issues', 'problems', 'errors']):
            state = self._handle_complex_question(state)
            state['iteration'] = iteration + 1
            return state
        
        # Parse action more intelligently
        action = self._parse_action_intelligently(action, question)
        
        state['action'] = action
        state['iteration'] = iteration + 1
        
        logger.info(f"Agent thought: {action} (iteration {state['iteration']}) for question: {question[:50]}...")
        return state
    
    def _parse_action_intelligently(self, llm_response: str, question: str) -> str:
        """Parse LLM response to extract the intended action more intelligently"""
        response_lower = llm_response.lower().strip()
        
        # First, look for exact action matches
        exact_actions = [
            "retrieve_altitude", "retrieve_battery", "retrieve_gps", 
            "retrieve_events", "retrieve_attitude", "detect_anomalies", 
            "ask_clarification", "answer"
        ]
        
        for action in exact_actions:
            if response_lower == action:
                return action
        
        # If no exact match, analyze the question context more intelligently
        question_lower = question.lower()
        
        # For specific questions, choose the most appropriate action
        if any(phrase in question_lower for phrase in [
            "highest altitude", "max altitude", "altitude reached", "how high"
        ]):
            return "retrieve_altitude"
        elif any(phrase in question_lower for phrase in [
            "battery temperature", "max temperature", "voltage", "battery"
        ]):
            return "retrieve_battery"
        elif any(phrase in question_lower for phrase in [
            "gps signal", "gps lost", "gps problem", "position"
        ]):
            return "retrieve_gps"
        elif any(phrase in question_lower for phrase in [
            "anomalies", "issues", "problems", "errors", "critical"
        ]):
            return "detect_anomalies"
        elif any(phrase in question_lower for phrase in [
            "events", "warnings", "alerts"
        ]):
            return "retrieve_events"
        else:
            return "retrieve_gps"  # Default fallback
    
    def _handle_complex_question(self, state: AgentState) -> AgentState:
        """Handle complex questions that need multiple data sources"""
        question = state['question'].lower()
        session_id = state['session_id']
        iteration = state.get('iteration', 0)
        
        # Define data retrieval sequence for complex questions
        if 'anomalies' in question or 'issues' in question:
            data_sequence = ['retrieve_events', 'retrieve_battery', 'detect_anomalies']
            if iteration < len(data_sequence):
                state['action'] = data_sequence[iteration]
            else:
                state['action'] = 'answer'
                state['should_continue'] = False
        
        return state
    
    def _act_node(self, state: AgentState) -> AgentState:
        """Execute the chosen action"""
        action = state['action']
        session_id = state['session_id']
        
        observation = ""
        
        try:
            # Check if data is available before trying to retrieve
            available_data = self._get_available_data_summary(session_id)
            
            if action == 'retrieve_gps':
                if not available_data.get('has_gps', False):
                    observation = "GPS data not available in this flight log"
                else:
                    data = self.telemetry.get_parameter_data(session_id, 'GPS')
                    if data.get('error'):
                        observation = f"Error retrieving GPS data: {data['error']}"
                    else:
                        observation = f"Retrieved GPS data: {data.get('count', 0)} points. "
                        if data.get('statistics'):
                            stats = data['statistics']
                            observation += f"Altitude range: {stats.get('min', 0):.1f}m to {stats.get('max', 0):.1f}m"
                        # Store retrieved data (append to existing data if multiple retrievals)
                        if 'retrieved_data' not in state:
                            state['retrieved_data'] = {}
                        state['retrieved_data'][data.get('parameter', 'GPS')] = data
            
            elif action == 'retrieve_battery':
                if not available_data.get('has_battery', False):
                    observation = "Battery data not available in this flight log"
                else:
                    data = self.telemetry.get_parameter_data(session_id, 'BATTERY')
                    if data.get('error'):
                        observation = f"Error retrieving battery data: {data['error']}"
                    else:
                        observation = f"Retrieved battery data: {data.get('count', 0)} points. "
                        if data.get('statistics'):
                            stats = data['statistics']
                            observation += f"Voltage range: {stats.get('min', 0):.1f}V to {stats.get('max', 0):.1f}V"
                        # Store retrieved data (append to existing data if multiple retrievals)
                        if 'retrieved_data' not in state:
                            state['retrieved_data'] = {}
                        state['retrieved_data'][data.get('parameter', 'BATTERY')] = data
            
            elif action == 'retrieve_altitude':
                if not available_data.get('has_gps', False):
                    observation = "Altitude data not available (no GPS data in this flight log)"
                else:
                    data = self.telemetry.get_parameter_data(session_id, 'ALTITUDE')
                    if data.get('error'):
                        observation = f"Error retrieving altitude data: {data['error']}"
                    else:
                        observation = f"Retrieved altitude data: {data.get('count', 0)} points. "
                        if data.get('statistics'):
                            stats = data['statistics']
                            observation += f"Range: {stats.get('min', 0):.1f}m to {stats.get('max', 0):.1f}m, Mean: {stats.get('mean', 0):.1f}m"
                        # Store retrieved data (append to existing data if multiple retrievals)
                        if 'retrieved_data' not in state:
                            state['retrieved_data'] = {}
                        state['retrieved_data'][data.get('parameter', 'ALTITUDE')] = data
            
            elif action == 'retrieve_attitude':
                if not available_data.get('has_attitude', False):
                    observation = "Attitude data not available in this flight log"
                else:
                    data = self.telemetry.get_parameter_data(session_id, 'ATTITUDE')
                    if data.get('error'):
                        observation = f"Error retrieving attitude data: {data['error']}"
                    else:
                        observation = f"Retrieved attitude data: {data.get('count', 0)} points available"
                        # Store retrieved data (append to existing data if multiple retrievals)
                        if 'retrieved_data' not in state:
                            state['retrieved_data'] = {}
                        state['retrieved_data'][data.get('parameter', 'ATTITUDE')] = data
            
            elif action == 'retrieve_events':
                if not available_data.get('has_events', False):
                    observation = "Event data not available in this flight log"
                else:
                    data = self.telemetry.get_parameter_data(session_id, 'EVENTS')
                    if data.get('error'):
                        observation = f"Error retrieving events: {data['error']}"
                    else:
                        observation = f"Retrieved {data.get('count', 0)} flight events"
                        # Store retrieved data (append to existing data if multiple retrievals)
                        if 'retrieved_data' not in state:
                            state['retrieved_data'] = {}
                        state['retrieved_data'][data.get('parameter', 'EVENTS')] = data
            
            elif action == 'detect_anomalies':
                anomalies = self.telemetry.detect_anomalies(session_id)
                observation = f"Detected {len(anomalies)} anomalies in flight data"
                if anomalies:
                    # Add details about anomalies
                    anomaly_types = [a.get('type', 'Unknown') for a in anomalies[:3]]
                    observation += f". Types: {', '.join(anomaly_types)}"
                state['anomalies'] = anomalies
            
            elif action == 'ask_clarification':
                # Ask user for clarification
                question = state['question']
                available_data = self._get_available_data_summary(session_id)
                
                clarification_prompt = f"""The user asked: "{question}"

Available data in this session:
- Vehicle: {available_data.get('vehicle_type', 'Unknown')}
- Available parameters: {', '.join(available_data.get('available_parameters', []))}

The question seems ambiguous or could be interpreted in multiple ways. Ask for clarification to provide the most helpful answer.

Generate a helpful clarification question that helps the user be more specific about what they want to know."""
                
                clarification = self.gemini.chat(clarification_prompt, system_prompt="You are a helpful flight data analyst. Ask clarifying questions to better understand what the user needs.")
                observation = f"Asked for clarification: {clarification}"
                state['should_continue'] = False
                state['answer'] = clarification
            
            elif action == 'rag_answer':
                # RAG-only answer using session collection + docs
                try:
                    vectors = self.gemini.embed_texts([state['question']]) or []
                    if vectors:
                        query_vector = vectors[0]
                        session_collection = f"session_{session_id}"
                        session_hits = self.qdrant.search_in_collection(session_collection, query_vector, top_k=5) or []
                        doc_hits = self.qdrant.search(query_vector, top_k=3) or []
                        # Build context
                        context_chunks = []
                        for hit in session_hits + doc_hits:
                            payload = hit.get('payload') or {}
                            text = payload.get('text')
                            if text:
                                context_chunks.append(text)
                        rag_context = "\n\n".join(context_chunks[:8])
                        # Ask model to answer only from context
                        answer = self.gemini.chat(
                            user_message=(
                                f"You must answer strictly using the CONTEXT below.\n\n"
                                f"CONTEXT:\n{rag_context}\n\nQUESTION: {state['question']}\n\n"
                                f"If needed, prefer terminology and interpretations consistent with the ArduPilot log messages documentation at https://ardupilot.org/plane/docs/logmessages.html."
                            ),
                            system_prompt=(
                                "You are a UAV telemetry and ArduPilot expert. Use only the provided context. "
                                "When interpreting message names, fields, and semantics, align with the ArduPilot documentation at the given URL. "
                                "If the context does not contain the required facts, say what additional data is needed."
                            )
                        )
                        state['answer'] = answer
                        observation = f"RAG used: {len(session_hits)} session hits, {len(doc_hits)} doc hits"
                    else:
                        observation = "RAG: could not generate embeddings"
                except Exception as e:
                    observation = f"RAG error: {e}"
                state['should_continue'] = False

            elif action == 'answer':
                state['should_continue'] = False
            
            else:
                observation = f"Unknown action '{action}', will proceed to answer"
                state['should_continue'] = False
        
        except Exception as e:
            observation = f"Error executing action: {str(e)}"
            logger.error(f"Action error: {e}")
        
        state['observation'] = observation
        logger.info(f"Agent observation: {observation}")
        
        return state
    
    def _should_continue(self, state: AgentState) -> str:
        """Decide whether to continue or respond"""
        if state.get('should_continue') == False:
            return "end"
        
        iteration = state.get('iteration', 0)
        max_iterations = state.get('max_iterations', 5)  # Increase from 3 to 5
        
        if iteration >= max_iterations:
            return "end"
        
        # For complex questions, allow multiple data retrievals
        question = state['question'].lower()
        if any(word in question for word in ['anomalies', 'issues', 'problems', 'errors', 'critical']):
            # Allow up to 3 iterations for anomaly detection
            if iteration < 3:
                return "continue"
        
        if state.get('action') == 'answer':
            return "end"
        
        # For simple questions, limit to 2 iterations
        if iteration >= 2 and not any(word in question for word in ['anomalies', 'issues']):
            return "end"
        
        return "continue"
    
    def _respond_node(self, state: AgentState) -> AgentState:
        """Generate final response with better data utilization"""
        question = state['question']
        session_id = state['session_id']
        retrieved_data = state.get('retrieved_data', {})
        anomalies = state.get('anomalies', [])
        observations = state.get('observation', '')
        
        # Get available data summary for context
        available_data = self._get_available_data_summary(session_id)
        
        # Prepare detailed context with retrieved data
        context = f"FLIGHT DATA ANALYSIS CONTEXT:\n"
        context += f"Vehicle: {available_data.get('vehicle_type', 'Unknown')}\n"
        context += f"Log Type: {available_data.get('log_type', 'Unknown')}\n"
        context += f"Available Parameters: {', '.join(available_data.get('available_parameters', []))}\n"
        context += f"Total Data Points: {available_data.get('data_points', 0)}\n"
        
        # Do not include local retrieved_data context; rely on RAG context only
        
        # Add observations
        if observations:
            context += f"\nANALYSIS OBSERVATIONS:\n{observations}\n"
        
        # Add anomalies
        if anomalies:
            context += f"\nDETECTED ANOMALIES ({len(anomalies)}):\n"
            for i, anomaly in enumerate(anomalies[:10], 1):
                context += f"{i}. {anomaly.get('type', 'Unknown')}: {anomaly.get('description', 'No description')}\n"
                if anomaly.get('timestamp'):
                    context += f"   Timestamp: {anomaly.get('timestamp')}\n"
                if anomaly.get('severity'):
                    context += f"   Severity: {anomaly.get('severity')}\n"
        
        # Use Gemini to generate comprehensive answer
        answer = self.gemini.analyze_telemetry(
            question=question,
            telemetry_data=retrieved_data if retrieved_data else {},
            context=context
        )
        
        state['answer'] = answer
        return state
    
    def _get_available_data_summary(self, session_id: str) -> Dict[str, Any]:
        """Get summary of available data for the session"""
        try:
            session = self.telemetry.session_manager.get_session(session_id)
            if not session or not session.flight_data:
                return {
                    'vehicle_type': 'Unknown',
                    'log_type': 'Unknown',
                    'available_parameters': [],
                    'has_gps': False,
                    'has_battery': False,
                    'has_attitude': False,
                    'has_events': False,
                    'data_points': 0
                }
            
            # Create summary using existing method
            summary = self.telemetry.session_manager._create_flight_summary(session_id, session.flight_data)
            
            return {
                'vehicle_type': summary.vehicle_type or 'Unknown',
                'log_type': summary.log_type or 'Unknown',
                'available_parameters': summary.available_parameters,
                'has_gps': summary.has_gps,
                'has_battery': summary.has_battery,
                'has_attitude': summary.has_attitude,
                'has_events': summary.has_events,
                'data_points': summary.data_points
            }
        except Exception as e:
            logger.error(f"Error getting data summary: {e}")
            return {
                'vehicle_type': 'Unknown',
                'log_type': 'Unknown',
                'available_parameters': [],
                'has_gps': False,
                'has_battery': False,
                'has_attitude': False,
                'has_events': False,
                'data_points': 0
            }

    def run(self, question: str, session_id: str, max_iterations: int = 3) -> str:
        """Run the agent to answer a question"""
        initial_state = {
            'question': question,
            'session_id': session_id,
            'thought': '',
            'action': '',
            'observation': '',
            'answer': '',
            'iteration': 0,
            'max_iterations': max_iterations,
            'should_continue': True
        }
        
        try:
            result = self.graph.invoke(initial_state)
            return result.get('answer', 'I apologize, but I could not generate an answer.')
        except Exception as e:
            logger.error(f"Error running agent: {e}")
            return f"I encountered an error while analyzing the data: {str(e)}"

