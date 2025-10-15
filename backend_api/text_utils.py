# text_utils.py - Text processing utilities for clean output

import re
import html
from typing import Dict, Any

def sanitize_text(text: str) -> str:
    """
    Sanitize text by removing special characters and ensuring plain text output.
    
    Args:
        text: Input text that may contain special characters
        
    Returns:
        Clean plain text string
    """
    if not text or not isinstance(text, str):
        return ""
    
    # Decode HTML entities first
    text = html.unescape(text)
    
    # Remove markdown formatting
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Bold
    text = re.sub(r'\*(.*?)\*', r'\1', text)      # Italic
    text = re.sub(r'`(.*?)`', r'\1', text)        # Code
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)  # Code blocks
    text = re.sub(r'`.*?`', '', text)             # Inline code
    
    # Remove URLs but keep the text
    text = re.sub(r'https?://[^\s]+', '', text)
    
    # Remove excessive whitespace and newlines
    text = re.sub(r'\n\s*\n', '\n\n', text)  # Multiple newlines to double
    text = re.sub(r'[ \t]+', ' ', text)      # Multiple spaces to single
    
    # Remove special Unicode characters but keep basic punctuation
    text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)\[\]\"\'\/\\]', '', text)
    
    # Clean up any remaining artifacts
    text = re.sub(r'[^\x00-\x7F]+', '', text)  # Remove non-ASCII characters
    
    # Final cleanup
    text = text.strip()
    
    return text

def format_sections_with_paragraphs(text: str) -> str:
    """
    Format text to ensure sections like suggestions, options, recommendations start on new paragraphs.
    
    Args:
        text: Input text that may contain section headers
        
    Returns:
        Text with proper paragraph formatting for sections
    """
    if not text:
        return text
    
    # Define section patterns that should start on new paragraphs
    section_patterns = [
        # All caps section headers (like ANALYSIS SUMMARY, KEY FINDINGS)
        r'(\n|^)(\s*)([A-Z][A-Z\s]+(?:SUMMARY|FINDINGS|ANALYSIS|RECOMMENDATIONS|LIMITATIONS|STEPS|DATA|CONCLUSIONS?|ACTIONS?))(\s*:?\s*)',
        # Regular section headers with emojis
        r'(\n|^)(\s*)(💡\s*)?(Suggestions?|Options?|Recommendations?|Next Steps?|Limitations?|Summary|Analysis|Findings?|Conclusions?|Actions?|Steps?)(\s*:?\s*)',
        r'(\n|^)(\s*)(🤔\s*)?(Clarification|Questions?|Context)(\s*:?\s*)',
        # Markdown headers
        r'(\n|^)(\s*)(##\s*)([A-Z][A-Z\s]+)(\s*:?\s*)',
        r'(\n|^)(\s*)(\*\*)([A-Z][A-Z\s]+)(\*\*)(\s*:?\s*)',
        # Mixed case section headers
        r'(\n|^)(\s*)(Available Data|Key Findings|Detailed Analysis|Analysis Summary|Recommendations|Limitations|Next Steps)(\s*:?\s*)'
    ]
    
    formatted_text = text
    
    # First, handle the specific case where sections are concatenated without spacing
    # Look for patterns like "ANALYSIS SUMMARY The flight data..." and add spacing
    formatted_text = re.sub(
        r'([A-Z][A-Z\s]+(?:SUMMARY|FINDINGS|ANALYSIS|RECOMMENDATIONS|LIMITATIONS|STEPS|DATA|CONCLUSIONS?|ACTIONS?))\s+([A-Z][a-z])',
        r'\1\n\n\2',
        formatted_text
    )
    
    # Handle specific patterns from the example output
    specific_patterns = [
        (r'(ANALYSIS SUMMARY)\s+([A-Z])', r'\1\n\n\2'),
        (r'(AVAILABLE DATA)\s+([A-Z])', r'\1\n\n\2'),
        (r'(KEY FINDINGS)\s+([-•])', r'\1\n\n\2'),
        (r'(DETAILED ANALYSIS)\s+([A-Z])', r'\1\n\n\2'),
        (r'(RECOMMENDATIONS)\s+([0-9])', r'\1\n\n\2'),
        (r'(LIMITATIONS)\s+([A-Z])', r'\1\n\n\2'),
        (r'(NEXT STEPS)\s+([0-9])', r'\1\n\n\2'),
        (r'(Suggestions:)\s+([A-Z])', r'\1\n\n\2')
    ]
    
    for pattern, replacement in specific_patterns:
        formatted_text = re.sub(pattern, replacement, formatted_text)
    
    # Clean up any triple newlines that might have been created
    formatted_text = re.sub(r'\n{3,}', '\n\n', formatted_text)
    
    # Apply each pattern to ensure sections start on new paragraphs
    for pattern in section_patterns:
        # Replace with double newline before section headers
        formatted_text = re.sub(
            pattern, 
            r'\n\n\g<0>', 
            formatted_text, 
            flags=re.IGNORECASE | re.MULTILINE
        )
    
    # Final cleanup of excessive newlines (more than 2 consecutive)
    formatted_text = re.sub(r'\n{3,}', '\n\n', formatted_text)
    
    # Ensure proper spacing around bullet points and lists
    formatted_text = re.sub(r'(\n)(\s*[-•*])(\s)', r'\1\n\2\3', formatted_text)
    
    return formatted_text.strip()

def clean_llm_response(response: str) -> str:
    """
    Clean LLM response to ensure it's plain text suitable for chat display.
    
    Args:
        response: Raw LLM response
        
    Returns:
        Cleaned plain text response
    """
    if not response:
        return "I'm sorry, I couldn't generate a response. Please try again."
    
    # Apply sanitization
    cleaned = sanitize_text(response)
    
    # Format sections to start on new paragraphs
    cleaned = format_sections_with_paragraphs(cleaned)
    
    # Ensure minimum length
    if len(cleaned.strip()) < 10:
        return "I understand your question, but I need more context to provide a helpful answer. Could you please provide more details?"
    
    # Ensure it ends with proper punctuation
    if not cleaned.endswith(('.', '!', '?')):
        cleaned += '.'
    
    return cleaned

def format_flight_data_text(flight_data: dict) -> str:
    """
    Format flight data as clean, readable text for RAG ingestion.
    Enhanced to include comprehensive GPS, battery, and telemetry data.
    
    Args:
        flight_data: Dictionary containing flight data
        
    Returns:
        Formatted plain text string
    """
    formatted_parts = []
    
    # Vehicle information
    if 'vehicle' in flight_data:
        formatted_parts.append(f"Vehicle Type: {flight_data['vehicle']}")
    
    # Metadata
    if 'metadata' in flight_data and flight_data['metadata']:
        metadata = flight_data['metadata']
        if 'startTime' in metadata:
            formatted_parts.append(f"Flight Start Time: {metadata['startTime']}")
    
    # Flight modes
    if 'flightModeChanges' in flight_data:
        modes = [mode[1] for mode in flight_data['flightModeChanges']]
        unique_modes = list(set(modes))
        formatted_parts.append(f"Flight Modes Used: {', '.join(unique_modes)}")
        formatted_parts.append(f"Total Mode Changes: {len(flight_data['flightModeChanges'])}")
    
    # Enhanced trajectory and GPS information
    if 'trajectories' in flight_data:
        for trajectory_name, trajectory_data in flight_data['trajectories'].items():
            if 'trajectory' in trajectory_data:
                trajectory = trajectory_data['trajectory']
                formatted_parts.append(f"GPS Trajectory Points: {len(trajectory)}")
                
                # Add altitude range if available
                altitudes = [point[2] for point in trajectory if len(point) > 2]
                if altitudes:
                    min_alt = min(altitudes)
                    max_alt = max(altitudes)
                    formatted_parts.append(f"Altitude Range: {min_alt:.1f} meters to {max_alt:.1f} meters")
                    formatted_parts.append(f"Maximum Altitude: {max_alt:.1f} meters")
                
                # Add GPS speed analysis if available
                if len(trajectory) > 1:
                    # Calculate flight duration from timestamps if available
                    if len(trajectory[0]) > 3:  # Has timestamp
                        start_time = trajectory[0][3]
                        end_time = trajectory[-1][3]
                        duration = (end_time - start_time) / 1000.0  # Convert to seconds
                        formatted_parts.append(f"Flight Duration: {duration:.1f} seconds")
                
                break
    
    # Enhanced events analysis
    if 'events' in flight_data:
        formatted_parts.append(f"Total Events: {len(flight_data['events'])}")
        
        # Analyze battery data
        battery_events = [e for e in flight_data['events'] if isinstance(e, dict) and 'battery_voltage' in e]
        if battery_events:
            voltages = [e['battery_voltage'] for e in battery_events]
            min_voltage = min(voltages)
            max_voltage = max(voltages)
            formatted_parts.append(f"Battery Voltage Range: {min_voltage:.1f}V to {max_voltage:.1f}V")
            formatted_parts.append(f"Minimum Battery Voltage: {min_voltage:.1f}V")
        
        # Analyze temperature data
        temp_events = [e for e in flight_data['events'] if isinstance(e, dict) and 'temperature' in e]
        if temp_events:
            temperatures = [e['temperature'] for e in temp_events]
            max_temp = max(temperatures)
            min_temp = min(temperatures)
            formatted_parts.append(f"Temperature Range: {min_temp:.1f}°C to {max_temp:.1f}°C")
            formatted_parts.append(f"Maximum Temperature: {max_temp:.1f}°C")
    
    # Enhanced GPS metadata analysis
    if 'gps_metadata' in flight_data:
        gps_meta = flight_data['gps_metadata']
        if 'status_changes' in gps_meta:
            formatted_parts.append(f"GPS Status Changes: {len(gps_meta['status_changes'])}")
        if 'satellite_counts' in gps_meta:
            sat_counts = gps_meta['satellite_counts']
            if sat_counts:
                min_sats = min(sat_counts)
                max_sats = max(sat_counts)
                formatted_parts.append(f"Satellite Count Range: {min_sats} to {max_sats}")
        if 'signal_quality' in gps_meta:
            hdop_values = [sq.get('hdop', 0) for sq in gps_meta['signal_quality'] if 'hdop' in sq]
            if hdop_values:
                max_hdop = max(hdop_values)
                formatted_parts.append(f"Maximum HDop: {max_hdop:.2f}")
        if 'accuracy_metrics' in gps_meta:
            hacc_values = [am.get('hacc', 0) for am in gps_meta['accuracy_metrics'] if 'hacc' in am]
            if hacc_values:
                max_hacc = max(hacc_values)
                formatted_parts.append(f"Maximum Horizontal Accuracy: {max_hacc:.2f}m")
    
    # RC input analysis
    if 'rc_inputs' in flight_data:
        rc_data = flight_data['rc_inputs']
        formatted_parts.append(f"RC Input Data Points: {len(rc_data)}")
        # Check for signal loss indicators
        signal_loss_events = [rc for rc in rc_data if rc.get('signal_lost', False)]
        if signal_loss_events:
            formatted_parts.append(f"RC Signal Loss Events: {len(signal_loss_events)}")
    
    # Mission data
    if 'mission' in flight_data:
        formatted_parts.append(f"Mission Commands: {len(flight_data['mission'])}")
    
    # Parameters
    if 'params' in flight_data:
        formatted_parts.append(f"Vehicle Parameters: {len(flight_data['params'])} parameters available")
    
    # Join all parts with clean formatting
    result = "Flight Data Summary:\n" + "\n".join(formatted_parts)
    
    return sanitize_text(result)
