"""
Configuration settings for the UAV Log Viewer Backend API
"""

import os

class Config:
    """Base configuration class"""
    
    # API Settings
    HOST = os.getenv('API_HOST', '0.0.0.0')
    PORT = int(os.getenv('API_PORT', 8000))
    DEBUG = os.getenv('API_DEBUG', 'True').lower() == 'true'
    
    # CORS Settings
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:8080').split(',')
    
    # Session Settings
    SESSION_TIMEOUT_HOURS = int(os.getenv('SESSION_TIMEOUT_HOURS', 24))
    MAX_SESSIONS = int(os.getenv('MAX_SESSIONS', 100))
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Data Limits
    MAX_FLIGHT_DATA_SIZE_MB = int(os.getenv('MAX_FLIGHT_DATA_SIZE_MB', 50))
    MAX_MESSAGE_LENGTH = int(os.getenv('MAX_MESSAGE_LENGTH', 1000))
    
    # Response Settings
    DEFAULT_RESPONSE_TIMEOUT = int(os.getenv('DEFAULT_RESPONSE_TIMEOUT', 30))

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    LOG_LEVEL = 'WARNING'

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'
    MAX_SESSIONS = 10

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
