# conversation_state.py - Agentic conversation state management

import json
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class ConversationIntent(Enum):
    """Types of conversation intents"""
    FLIGHT_ANALYSIS = "flight_analysis"
    TELEMETRY_QUERY = "telemetry_query"
    SYSTEM_DIAGNOSTIC = "system_diagnostic"
    GENERAL_QUESTION = "general_question"
    CLARIFICATION_NEEDED = "clarification_needed"
    DOCUMENTATION_REQUEST = "documentation_request"

class ConversationState(Enum):
    """States of the conversation"""
    INITIAL = "initial"
    GATHERING_CONTEXT = "gathering_context"
    ANALYZING = "analyzing"
    CLARIFYING = "clarifying"
    PROVIDING_ANSWER = "providing_answer"
    FOLLOW_UP = "follow_up"

@dataclass
class ConversationContext:
    """Context information for the conversation"""
    session_id: str
    current_state: ConversationState
    intent: Optional[ConversationIntent]
    flight_data_available: bool
    telemetry_queries: List[str]
    clarification_requests: List[str]
    conversation_history: List[Dict[str, Any]]
    last_activity: float
    confidence_score: float
    missing_information: List[str]
    suggested_actions: List[str]

@dataclass
class ClarificationRequest:
    """Structure for clarification requests"""
    question: str
    context: str
    options: List[str]
    required: bool
    follow_up_actions: List[str]

class AgenticConversationManager:
    """Manages agentic conversation state and proactive interactions"""
    
    def __init__(self):
        self.conversations: Dict[str, ConversationContext] = {}
        self.ardupilot_docs_cache: Dict[str, str] = {}
        self.telemetry_patterns = {
            'attitude': ['ATT', 'ATTITUDE', 'ROLL', 'PITCH', 'YAW'],
            'position': ['GPS', 'POSITION', 'LAT', 'LON', 'ALT'],
            'velocity': ['VEL', 'VELOCITY', 'SPEED', 'VX', 'VY', 'VZ'],
            'battery': ['BAT', 'BATTERY', 'VOLT', 'CURRENT', 'MAH'],
            'sensors': ['IMU', 'ACCEL', 'GYRO', 'MAG', 'BARO'],
            'navigation': ['NAV', 'WP', 'WAYPOINT', 'MISSION'],
            'modes': ['MODE', 'FLTMODE', 'FLIGHT_MODE'],
            'errors': ['ERR', 'ERROR', 'WARN', 'WARNING', 'FAIL']
        }
    
    def get_or_create_context(self, session_id: str) -> ConversationContext:
        """Get existing conversation context or create new one"""
        if session_id not in self.conversations:
            self.conversations[session_id] = ConversationContext(
                session_id=session_id,
                current_state=ConversationState.INITIAL,
                intent=None,
                flight_data_available=False,
                telemetry_queries=[],
                clarification_requests=[],
                conversation_history=[],
                last_activity=time.time(),
                confidence_score=0.0,
                missing_information=[],
                suggested_actions=[]
            )
        return self.conversations[session_id]
    
    def update_conversation_state(self, session_id: str, message: str, response: str, 
                                flight_data_available: bool = False) -> ConversationContext:
        """Update conversation state based on message and response"""
        context = self.get_or_create_context(session_id)
        
        # Update basic info
        context.last_activity = time.time()
        context.flight_data_available = flight_data_available
        
        # Add to conversation history
        context.conversation_history.append({
            'timestamp': time.time(),
            'user_message': message,
            'assistant_response': response,
            'state': context.current_state.value
        })
        
        # Analyze intent and update state
        intent = self._analyze_intent(message, context)
        context.intent = intent
        
        # Update state based on intent and context
        context.current_state = self._determine_next_state(context, message, response)
        
        # Generate proactive suggestions
        context.suggested_actions = self._generate_suggestions(context)
        
        # Check for missing information
        context.missing_information = self._identify_missing_info(context, message)
        
        return context
    
    def _analyze_intent(self, message: str, context: ConversationContext) -> ConversationIntent:
        """Analyze user intent from message"""
        message_lower = message.lower()
        
        # Check for telemetry-related queries
        for category, patterns in self.telemetry_patterns.items():
            if any(pattern.lower() in message_lower for pattern in patterns):
                return ConversationIntent.TELEMETRY_QUERY
        
        # Check for flight analysis intent
        analysis_keywords = ['analyze', 'analysis', 'flight', 'log', 'data', 'performance', 'issue']
        if any(keyword in message_lower for keyword in analysis_keywords):
            return ConversationIntent.FLIGHT_ANALYSIS
        
        # Check for system diagnostic intent
        diagnostic_keywords = ['error', 'problem', 'issue', 'fail', 'warning', 'diagnose']
        if any(keyword in message_lower for keyword in diagnostic_keywords):
            return ConversationIntent.SYSTEM_DIAGNOSTIC
        
        # Check for documentation request
        doc_keywords = ['documentation', 'docs', 'reference', 'explain', 'what is', 'how does']
        if any(keyword in message_lower for keyword in doc_keywords):
            return ConversationIntent.DOCUMENTATION_REQUEST
        
        return ConversationIntent.GENERAL_QUESTION
    
    def _determine_next_state(self, context: ConversationContext, message: str, response: str) -> ConversationState:
        """Determine the next conversation state"""
        current_state = context.current_state
        
        # State transitions based on context
        if current_state == ConversationState.INITIAL:
            if context.intent == ConversationIntent.TELEMETRY_QUERY and not context.flight_data_available:
                return ConversationState.CLARIFYING
            elif context.intent in [ConversationIntent.FLIGHT_ANALYSIS, ConversationIntent.SYSTEM_DIAGNOSTIC]:
                return ConversationState.GATHERING_CONTEXT
            else:
                return ConversationState.PROVIDING_ANSWER
        
        elif current_state == ConversationState.GATHERING_CONTEXT:
            if context.missing_information:
                return ConversationState.CLARIFYING
            else:
                return ConversationState.ANALYZING
        
        elif current_state == ConversationState.CLARIFYING:
            if "?" in message or any(word in message.lower() for word in ['yes', 'no', 'sure', 'ok']):
                return ConversationState.ANALYZING
            else:
                return ConversationState.CLARIFYING
        
        elif current_state == ConversationState.ANALYZING:
            return ConversationState.PROVIDING_ANSWER
        
        elif current_state == ConversationState.PROVIDING_ANSWER:
            return ConversationState.FOLLOW_UP
        
        else:  # FOLLOW_UP
            return ConversationState.FOLLOW_UP
    
    def _generate_suggestions(self, context: ConversationContext) -> List[str]:
        """Generate proactive suggestions based on context"""
        suggestions = []
        
        if context.intent == ConversationIntent.TELEMETRY_QUERY:
            if not context.flight_data_available:
                suggestions.append("Would you like me to help you load flight data for analysis?")
            else:
                suggestions.append("I can analyze specific telemetry parameters. Which ones interest you?")
        
        elif context.intent == ConversationIntent.FLIGHT_ANALYSIS:
            if context.flight_data_available:
                suggestions.extend([
                    "I can analyze flight performance metrics",
                    "Would you like me to check for any anomalies or issues?",
                    "I can compare this flight with typical patterns"
                ])
            else:
                suggestions.append("Please load flight data so I can provide detailed analysis")
        
        elif context.intent == ConversationIntent.SYSTEM_DIAGNOSTIC:
            suggestions.extend([
                "I can check error logs and system health",
                "Would you like me to analyze sensor data for issues?",
                "I can help identify potential causes of problems"
            ])
        
        # Add general suggestions
        if len(context.conversation_history) > 3:
            suggestions.append("Is there anything specific about this flight you'd like me to investigate further?")
        
        return suggestions[:3]  # Limit to 3 suggestions
    
    def _identify_missing_info(self, context: ConversationContext, message: str) -> List[str]:
        """Identify missing information that could improve the response"""
        missing = []
        
        # Only identify missing info if we're in early conversation stages or if the question is clearly incomplete
        if len(context.conversation_history) > 3:
            # After a few exchanges, be more conservative about requesting clarification
            return missing
        
        if context.intent == ConversationIntent.TELEMETRY_QUERY:
            if not context.flight_data_available:
                # Only request flight data if the question clearly requires it
                message_lower = message.lower()
                if any(word in message_lower for word in ['analyze', 'flight', 'log', 'data', 'telemetry', 'gps', 'battery']):
                    missing.append("flight_data")
        
        elif context.intent == ConversationIntent.FLIGHT_ANALYSIS:
            if not context.flight_data_available:
                # Only request flight data if the question clearly requires it
                message_lower = message.lower()
                if any(word in message_lower for word in ['analyze', 'flight', 'log', 'data', 'performance', 'safety']):
                    missing.append("flight_data")
        
        return missing
    
    def should_request_clarification(self, context: ConversationContext) -> Optional[ClarificationRequest]:
        """Determine if clarification is needed and return request"""
        if not context.missing_information:
            return None
        
        # Don't request clarification if we're in an established conversation
        # unless the question is clearly incomplete or ambiguous
        if len(context.conversation_history) > 2:
            # Only request clarification for critical missing information
            if "flight_data" in context.missing_information and context.intent in [ConversationIntent.TELEMETRY_QUERY, ConversationIntent.FLIGHT_ANALYSIS]:
                # Check if the last response was helpful
                if context.conversation_history:
                    last_response = context.conversation_history[-1].get('assistant_response', '')
                    # If the response was comprehensive, don't request clarification
                    if len(last_response) > 100 and not any(phrase in last_response.lower() for phrase in ['need more', 'unclear', 'ambiguous']):
                        return None
                
                return ClarificationRequest(
                    question="I notice you're asking about flight data, but I don't see any loaded. Would you like me to help you load flight data for analysis?",
                    context="Flight data analysis requires telemetry information",
                    options=["Yes, load flight data", "No, continue without data", "Show me how to load data"],
                    required=True,
                    follow_up_actions=["load_flight_data", "provide_general_info", "show_loading_instructions"]
                )
        
        # For early conversation, be more helpful with clarification
        if "flight_data" in context.missing_information:
            return ClarificationRequest(
                question="I notice you're asking about flight data, but I don't see any loaded. Would you like me to help you load flight data for analysis?",
                context="Flight data analysis requires telemetry information",
                options=["Yes, load flight data", "No, continue without data", "Show me how to load data"],
                required=True,
                follow_up_actions=["load_flight_data", "provide_general_info", "show_loading_instructions"]
            )
        
        if "analysis_focus" in context.missing_information:
            return ClarificationRequest(
                question="What aspect of the flight would you like me to focus on?",
                context="Flight analysis can cover multiple areas",
                options=["Performance metrics", "Safety analysis", "Efficiency review", "Error detection", "All of the above"],
                required=False,
                follow_up_actions=["analyze_performance", "analyze_safety", "analyze_efficiency", "detect_errors", "comprehensive_analysis"]
            )
        
        if "time_range" in context.missing_information:
            return ClarificationRequest(
                question="What time period are you interested in analyzing?",
                context="Time-based analysis requires specific time ranges",
                options=["Entire flight", "Specific time range", "Takeoff phase", "Landing phase", "Cruise phase"],
                required=False,
                follow_up_actions=["analyze_full_flight", "analyze_time_range", "analyze_takeoff", "analyze_landing", "analyze_cruise"]
            )
        
        return None
    
    def get_conversation_summary(self, session_id: str) -> Dict[str, Any]:
        """Get a summary of the conversation state"""
        if session_id not in self.conversations:
            return {"error": "No conversation found"}
        
        context = self.conversations[session_id]
        return {
            "session_id": session_id,
            "current_state": context.current_state.value,
            "intent": context.intent.value if context.intent else None,
            "flight_data_available": context.flight_data_available,
            "conversation_length": len(context.conversation_history),
            "last_activity": context.last_activity,
            "confidence_score": context.confidence_score,
            "missing_information": context.missing_information,
            "suggested_actions": context.suggested_actions,
            "recent_messages": context.conversation_history[-3:] if context.conversation_history else []
        }
    
    def cleanup_old_conversations(self, max_age_hours: int = 24) -> int:
        """Clean up old conversation contexts"""
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        to_remove = []
        for session_id, context in self.conversations.items():
            if current_time - context.last_activity > max_age_seconds:
                to_remove.append(session_id)
        
        for session_id in to_remove:
            del self.conversations[session_id]
        
        return len(to_remove)

# Global conversation manager instance
_global_conversation_manager = None

def get_global_conversation_manager() -> AgenticConversationManager:
    """Get the global conversation manager instance"""
    global _global_conversation_manager
    if _global_conversation_manager is None:
        _global_conversation_manager = AgenticConversationManager()
    return _global_conversation_manager
