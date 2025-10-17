from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ChatMessage:
    """Chat message model"""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class SessionData:
    """Session data model"""
    session_id: str
    flight_data: Dict[str, Any] = field(default_factory=dict)
    conversation_history: List[ChatMessage] = field(default_factory=list)
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    last_activity: float = field(default_factory=lambda: datetime.now().timestamp())
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now().timestamp()
    
    def add_message(self, role: str, content: str):
        """Add message to conversation history"""
        self.conversation_history.append(ChatMessage(role=role, content=content))
        self.update_activity()
    
    def get_recent_history(self, limit: int = 10) -> List[Dict[str, str]]:
        """Get recent conversation history"""
        recent = self.conversation_history[-limit:]
        return [{'role': msg.role, 'content': msg.content} for msg in recent]


@dataclass
class FlightDataSummary:
    """Summary of available flight data"""
    session_id: str
    vehicle_type: Optional[str] = None
    log_type: Optional[str] = None
    available_parameters: List[str] = field(default_factory=list)
    has_gps: bool = False
    has_battery: bool = False
    has_attitude: bool = False
    has_events: bool = False
    flight_duration: Optional[float] = None
    data_points: int = 0

