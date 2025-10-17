import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration"""
    
    # Google Gemini
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', '')
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-1.5-pro')
    
    # Qdrant Cloud (using your existing .env variable names)
    QDRANT_URL = os.getenv('QDRANT_URL', '')
    QDRANT_API_KEY = os.getenv('QDRANT_API_KEY', '')
    
    # Flask
    FLASK_PORT = int(os.getenv('FLASK_PORT', 8000))
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    # Session
    SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', 3600))
    
    # Agent
    MAX_AGENT_ITERATIONS = int(os.getenv('MAX_AGENT_ITERATIONS', 5))
    
    # ArduPilot Documentation
    ARDUPILOT_DOCS_URL = 'https://ardupilot.org/plane/docs/logmessages.html'
    
    # Optional web/tool usage (opt-in triggers)
    WEB_TOOL_ENABLED = os.getenv('WEB_TOOL_ENABLED', 'true').lower() == 'true'
    WEB_TOOL_TRIGGERS = os.getenv('WEB_TOOL_TRIGGERS', 'use web,search web,search docs,from docs,duckduckgo,ddg').split(',')
    WEB_TOOL_MAX_CHARS = int(os.getenv('WEB_TOOL_MAX_CHARS', 8000))
    WEB_SEARCH_SITE_LIMIT = os.getenv('WEB_SEARCH_SITE_LIMIT', 'ardupilot.org')
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is required")
        return True

