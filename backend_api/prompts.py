"""
System prompts for the UAV Log Viewer Backend API
"""

# Main system prompt for ArduPilot data analysis
ARDUPILOT_DATA_ANALYST_PROMPT = """You are a data analyst for ArduPilot data, answer all of the questions of the user. Refer the internet whenever required."""

# Alternative prompts for different use cases
UAV_LOG_ANALYSIS_PROMPT = """You are a helpful AI assistant specialized in UAV log analysis and flight data interpretation. 
You can help users understand flight logs, analyze telemetry data, and provide insights about UAV operations."""

FLIGHT_DATA_EXPERT_PROMPT = """You are an expert in flight data analysis and UAV operations. 
You can analyze telemetry data, identify patterns, troubleshoot issues, and provide detailed insights about flight performance."""

# Dictionary of available prompts
AVAILABLE_PROMPTS = {
    "ardupilot_analyst": ARDUPILOT_DATA_ANALYST_PROMPT,
    "uav_log_analysis": UAV_LOG_ANALYSIS_PROMPT,
    "flight_data_expert": FLIGHT_DATA_EXPERT_PROMPT
}

def get_prompt(prompt_name: str = "ardupilot_analyst") -> str:
    """
    Get a system prompt by name.
    
    Args:
        prompt_name: Name of the prompt to retrieve
        
    Returns:
        The system prompt string
        
    Raises:
        KeyError: If prompt_name is not found in AVAILABLE_PROMPTS
    """
    if prompt_name not in AVAILABLE_PROMPTS:
        raise KeyError(f"Prompt '{prompt_name}' not found. Available prompts: {list(AVAILABLE_PROMPTS.keys())}")
    
    return AVAILABLE_PROMPTS[prompt_name]

def list_available_prompts() -> list:
    """
    Get a list of all available prompt names.
    
    Returns:
        List of prompt names
    """
    return list(AVAILABLE_PROMPTS.keys())
